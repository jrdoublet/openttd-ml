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

/* Declare avant les require() : catalog.nut consulte ce drapeau dans son cycle annuel. Repli
 * actif jusqu'a la lecture unique de road_mode dans Start(), comme les autres reglages de
 * decision. Le defaut vrai est celui de info.nut ; 0 reconstitue la baseline sans route, dont le
 * chemin d'opcodes reste alors EXACTEMENT celui des campagnes anterieures. */
ROAD_BUILD_ENABLED <- true;
/* Cascade pax par distance decroissante : air seul, air+rail, rail seul,
 * route seule. Le fret accompagne la premiere passe. */
STAGED_BOOTSTRAP <- true;

/* Les bus ville-a-ville sont utiles dans la bande courte, mais peuvent prendre le bassin d'une
 * liaison aerienne plus rentable. Ce drapeau ne coupe que cette famille de nouveaux candidats :
 * fret routier, feeders vers les hubs et lignes deja construites restent actifs. Le defaut faux
 * privilegie le profit des aeroports ; le banc peut reconstituer le bras bus avec
 * road_pax_build = 1. */
ROAD_PAX_BUILD_ENABLED <- false;

/* Part du bassin de ville propre aux bus. 86 est le calibrage route adopte au banc.
 * Le reglage road_pax_catchment_pct vaut 0 pour reconstituer le repli rail a 22 % ; une valeur
 * positive ne touche que OpexRoadPaxCandidates, jamais le rail ni le fret. */
ROAD_PAX_CATCHMENT_SHARE_PCT <- 86;
/* C23/D4 : Borne physique d'un arret de bus (rayon 3 tuiles = 7x7 tuiles = moyenne 10 maisons sur grille de voirie) */
ROAD_STOP_CATCHMENT_HOUSES <- 10;
/* D4 : Dwell time de chargement/dechargement a la station pour les bus passagers (jours) */
ROAD_PAX_STOP_DWELL_DAYS <- 6;
/* D4, extension aerienne : le diagnostic 10 ans x 5 graines
 * (results/diag_road_purpose.json) donne revenu reel/predit median = 1,0427 pour
 * air|pax. Le modele etait donc legerement conservateur. Ce facteur ne touche
 * que le revenu passager aerien, avant le calcul du profit et des scores. */
AIR_PAX_REVENUE_CALIBRATION_PCT <- 104;
/* C27 : Sortir les bonus du numerateur de densite du portefeuille (adopte) */
CLEAN_DENSITY_SCORE <- true;
/* C28 : Maximum glissant sur les N derniers cycles pour capitalCeiling (defaut 24) */
CAPITAL_CEILING_CYCLES <- 24;
/* C29.1 + C29.2 : Deverrouillage du rabattement (feeders) vers hubs aeriens et ferroviaires */
FEEDER_UNLOCK <- true;
/* C29.3 : Pricing du feeder calculé sur le revenu hub et le bassin de captage */
FEEDER_PRICING <- true;
/* C29.4 : Couverture multi-arrêts urbaine pour rabattement (modèle AAAHogEx) */
FEEDER_TOWN_COVERAGE <- true;
/* C29.5 : Duplication des bus de rabattement passagers par des camions postaux (modèle AAAHogEx #M1) */
FEEDER_MAIL_DUPLICATE <- true;
/* Conditionnement des feeders au besoin reel du hub (maturite et stock insuffisant) */
FEEDER_HUB_CHECK <- true;
FEEDER_HUB_WAIT_MAX <- 100;
FEEDER_HUB_MIN_DAYS <- 60;

/* Panneaux de diagnostic : lu UNE fois depuis le reglage dans Start(), pas a chaque appel (57
 * panneaux par an, GetSetting a chaque fois serait du gaspillage d'opcodes pour une valeur qui ne
 * change jamais en cours de partie). Defaut vrai : voir info.nut::debug_signs -- toute
 * l'instrumentation de sweeps/*.py passe par ces panneaux, AILog.Info n'etant pas capture par
 * OpenTTDLab. On ne les coupe que pour une partie avec des humains. */
DEBUG_SIGNS <- true;


/* Mesure ponctuelle : un panneau par ligne reussie, donc desactivee par defaut pour ne pas
 * changer le profil d'opcodes de la baseline. */
RAIL_COST_PROBE <- false;
/* Symetrique aerien de RAIL_COST_PROBE : un panneau AC| par tentative, reussie ou non. C'est le
 * seul moyen de chiffrer le nivellement et les aeroports batis puis rases (§0 unvicies). */
AIR_COST_PROBE <- false;
/* Symetrique route de RAIL_COST_PROBE/AIR_COST_PROBE, jamais construit avant (docs/taches.md,
 * retrouve le 2026-09-08). Panneau RP| par tentative, reussie ou non (RC| deja pris). */
ROAD_COST_PROBE <- false;
/* air_presite : sonder les deux sites en AITestMode avant d'engager le capital du premier
 * aeroport. Inerte par defaut jusqu'au verdict du banc. */
AIR_PRESITE <- false;
/* C33.2 : Arrets de rabattement joints dans le chantier aeroport */
AIR_JOINED_STOPS <- false;
/* Refaire le sac a dos contre la caisse vivante, sans repayer la generation des candidats. */
PORTFOLIO_FRESH_BUDGET <- false;
/* C36.1 : Caching incremental du vivier post-chantier. */
PORTFOLIO_CACHE <- false;
/* C39.0 : sonde passive du bus d'invalidation. A 1, les evenements marquent les
 * dependances qui SERAIENT rafraichies et journalisent la passe mensuelle actuelle ;
 * ils ne changent ni sa cadence, ni les candidats, ni les decisions. */
C39_INVALIDATION_PROBE <- false;
/* C39.3 : sonde de l'effet réel d'une invalidation sur le catalogue et le premier projet. */
C39_DECISION_DELTA_PROBE <- false;
/* C39.4 : explique pourquoi un EngineAvailable air n'est pas retenu par les combos. */
C39_AIR_REASON_PROBE <- false;
/* C39.2 : premier consommateur actif, limite aux nouveaux moteurs ; reste experimental. */
C39_ENGINE_REFRESH <- false;
/* C41.0 : registre passif revision/acquittement pour les futures micro-taches ciblees. */
C41_REVISION_PROBE <- false;
/* C41.1 : consomme seulement catalog.water ; candidat/portefeuille restent au flux historique. */
C41_WATER_REFRESH <- false;
/* C41.2 : prefiltre local un moteur eau avant d'armer C41.1 ; experimental et eteint. */
C41_WATER_PRECHECK <- false;
/* C41.3 : sonde passive du cout de OpexWaterPlans apres C41.1/C41.2. */
C41_WATER_CANDIDATE_PROBE <- false;
/* C41.3a : ventile la sonde eau en sites, paires, BFS et economie ; aucun candidat persistant. */
C41_WATER_PLANS_PROFILE <- false;
/* C41.3b : sous-ventilation de la phase dominante sites : filtre carte vs AITestMode dock. */
C41_WATER_SITE_PROFILE <- false;
/* BFS maritime reconstruit sur MinchinWeb.Lakes (2026-09-09) -- voir docs/taches.md et
 * ai/OpexAI/lib_water.nut. Defaut aligne sur info.nut (custom_value = 1). */
WATER_LAKES_CONNECTIVITY <- true;
/* Catalogue persistant par ville des sites de dock (positifs et negatifs exhaustifs). Le
 * reglage 0 conserve le rescannage historique uniquement pour le banc apparie. */
WATER_SITE_CATALOG <- false;
/* Fronts de quai calculés à la découverte : expérimental jusqu'au diagnostic, car il change
 * l'éligibilité des sites eau. */
WATER_DISCOVERY_REAL_FRONTS <- false;
/* C41.11 : ledger passif du scheduler. Il n'admet ni ne reporte aucune tache. */
C41_SLACK_LEDGER <- false;
/* C41 : attribution mensuelle du temps du controleur, uniquement pour diagnostic. */
C41_MONTHLY_BUSY_LEDGER <- false;
/* C41.12 : age de fraicheur par couche entre premier salissement coalesce et acquittement. */
C41_STALENESS_LEDGER <- false;
/* C41.13 : croise passivement les couches encore sales avec le reliquat d'opcodes du scheduler.
 * Il ne choisit ni ne reporte aucune tache : il borne d'abord le canal de delestage possible. */
C41_OPPORTUNITY_LEDGER <- false;
/* C41.14 : contrat passif d'admission d'une micro-tache. Le seul pilote declare est le petit
 * refresh water ; ajouter route/rail/air exige d'abord leur point d'entree cible et son cout. */
C41_ADMISSION_LEDGER <- false;
/* C41.15 : rafraichissement cible du materiel route apres EngineAvailable route. */
C41_ROAD_REFRESH <- false;
/* C41.16 : ventilation passive de la generation de candidats route historique. */
C41_ROAD_CANDIDATE_PROFILE <- false;
/* C41.17 : sous-ventilation passive du fret producteur->accepteur. */
C41_ROAD_FREIGHT_PROFILE <- false;
/* C41.18 : index spatial local des origines fret route deja desservies. */
C41_ROAD_FREIGHT_SERVED_INDEX <- false;
/* C41.19 : profil passif interne des puits urbains du fret route. */
C41_ROAD_FREIGHT_TOWN_PROFILE <- false;
/* C41.20 : index experimental des puits urbains acceptant le cargo fret. */
C41_ROAD_FREIGHT_ACCEPTANCE_INDEX <- false;
/* C41.21 : ventilation passive des deux generations de feeders. */
C41_ROAD_FEEDER_PROFILE <- false;
/* C41.22 : cout et debit du pipeline rail vers le portefeuille, sans preemption. */
C41_RAIL_PORTFOLIO_PROFILE <- false;
/* C41.23 : ventilation passive de la generation rail pax/fret/classement. */
C41_RAIL_CANDIDATE_PROFILE <- false;
/* C41.24 : sous-ventilation passive des paires passagers rail. */
C41_RAIL_PAX_PROFILE <- false;
/* C41.25 : sous-ventilation passive du helper de candidature pax rail. */
C41_RAIL_PAX_CANDIDATE_PROFILE <- false;
/* C41.26 : sous-ventilation passive de l'economie pax rail. */
C41_RAIL_PAX_ECONOMICS_PROFILE <- false;
/* C41.27 : detail passif vitesse effective dans l'economie pax rail. */
C41_RAIL_PAX_SPEED_PROFILE <- false;
/* C41.28 : detail et reutilisation exacte des calculs de vitesse pax rail. */
C41_RAIL_PAX_SPEED_DETAIL_PROFILE <- false;
/* C41.29 : reutilisation exacte de la vitesse de croisiere pax rail. */
C41_RAIL_PAX_CRUISE_PROFILE <- false;
/* C41.30 : cache de croisiere pax, limite a une generation de candidats rail. */
C41_RAIL_PAX_CRUISE_CACHE <- false;
/* C41.31 : ventilation passive du fret rail. */
C41_RAIL_FREIGHT_PROFILE <- false;
/* C41.32 : coût des candidats dans les deux branches fret rail. */
C41_RAIL_FREIGHT_CANDIDATE_PROFILE <- false;
C41_RAIL_FREIGHT_ECONOMICS_PROFILE <- false;
C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE <- false;
C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE <- false;
C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE <- false;
/* C41.37/C41.38 : reutilisation exacte puis cache de croisiere fret, local a une generation. */
C41_RAIL_FREIGHT_CRUISE_PROFILE <- false;
C41_RAIL_FREIGHT_CRUISE_CACHE <- false;
C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE <- false;
C41_RAIL_FREIGHT_ACCELERATION_CACHE <- false;
C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE <- false;
C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE <- false;
C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE <- false;
/* C41.4 : sonde strictement passive des vehicules perdus. Contrairement a A7.4,
 * elle n'ecrit ni compteur de ligne ni signe, et n'arme aucune tache. */
C41_VEHICLE_LOST_PROBE <- false;
/* C41.5 : détail rail de C41.4 ; aucune réparation, seulement l'état observable au Lost. */
C41_RAIL_LOST_PROBE <- false;
/* C54 : inventaire annuel des vehicules via API, strictement inerte hors reglage dedie. */
C54_VEHICLE_ORDERS_PROBE <- false;
/* C41.6 : corrélation de topologie persistée des mêmes Lost rail, sans action. */
C41_RAIL_LOST_TOPOLOGY_PROBE <- false;
/* C41.7 : lecture locale des approches/depots d'une ligne double en Lost, sans route ni mutation. */
C41_RAIL_LOST_PHYSICAL_PROBE <- false;
/* C41.8 : réparation expérimentale, idempotente et limitée aux approches simples d'une ligne
 * double ayant réellement émis VehicleLost. */
C41_RAIL_LOST_SIGNAL_REPAIR <- false;
/* C41.9 : sonde locale de connectivite, sans recherche de chemin ni commande. */
C41_RAIL_LOST_CONNECTIVITY_PROBE <- false;
/* C41.10 : reparation transactionnelle du seul raccord manque identifie par C41.9 (une branche
 * candidate non ambigue) -- AITestMode d'abord, commande reelle seulement si le meme raccord
 * reussit en test. */
C41_RAIL_LOST_JUNCTION_REPAIR <- false;
/* C41.46 : separe les opcodes nets d'une tranche _continueRailSearch() de ceux de la tache de
 * file executee dans la MEME passe de _runNextTask (main.nut A4) -- le ledger C41.11 agrege les
 * deux des que _railSearch est non nul en entree de passe. Purement observatoire. */
C41_RAIL_SLICE_LEDGER <- false;
/* C41.47 : pendant de la garde G3S1 (plan en echec) applique au blocage tresorerie --
 * _consumeRailSearch() libere _railSearch des le premier blocage cash au lieu de le garder
 * indefiniment, ce qui debloque _expandRailLines et les AUTRES candidats rail du portefeuille.
 * candidate.railPlan est conserve. Correctif de blocage, pas un arbitrage.
 * ADOPTE au banc officiel 20x10 (2026-09-09) : voir info.nut pour les chiffres. */
C41_RAIL_CASH_RELEASE <- true;
/* C41.48 : sonde passive a chaque frontiere de tranche segmentee (CONT/done=false). Rien n'est
 * coupe ; mesure si un test de domination (C41.49) aurait meme l'occasion de se declencher. */
C41_RAIL_DOMINATION_PROBE <- false;
/* C41.49 (reformule 2026-09-10, docs/04_arbitrage_rail_search.md) : sonde passive dans
 * _tryBuildProjects, active seulement pendant une recherche rail (kind=="primary",
 * phase=="search", meme garde que C41.48). Ne coupe rien : mesure si le fallthrough du
 * portefeuille (un candidat rail rejete search_in_progress n'interrompt pas la boucle) essaie et
 * construit deja les alternatives non-rail que C41.48 voit financables a la frontiere -- avant
 * d'ecrire une regle de decision, savoir si elle a deja lieu par defaut. */
C41_PROJECTS_FALLTHROUGH_PROBE <- false;
/* C39.5 : sonde passive de cadence de la tache projects. Le repli 0 ne doit ajouter ni appel
 * d'API ni calcul au chemin livre ; voir docs/05_cadence_projects_rail_search.md. */
C39_PROJECTS_CADENCE_PROBE <- false;
/* C39.6 (docs/05_cadence_projects_rail_search.md §4.3) : mesure le delta date/tick/opcodes d'une
 * passe de _runNextTask, decompose entre la seule tranche A* et la tache de file jouee dans la
 * MEME passe, ventile par nom de tache et par presence de tranche. Reglage NOUVEAU et
 * INDEPENDANT de C41_RAIL_SLICE_LEDGER : ne pas etendre ce dernier, sa mesure est deja publiee.
 * Le repli 0 ne doit ajouter ni appel d'API ni calcul au chemin livre. */
C39_PASS_CLOCK_LEDGER <- false;
/* C48 (fiche C48) : ventilation passive des tentatives de _tryBuildProjects. Les dates et
 * marqueurs d'opcodes restent strictement derriere ce drapeau afin que le chemin livre n'ajoute
 * aucun appel d'API ni calcul. */
C48_PROJECT_ATTEMPT_LEDGER <- false;
/* C49 etape 1 : sonde strictement observatoire de la cause prochaine du projet non bati.
 * Le repli 0 ne doit atteindre ni lecture de tresorerie finale, ni plafond de vehicules, ni
 * allocation de ledger. */
C49_SCARCITY_LEDGER <- false;
/* C55 etape 1 : mesure seule du filtre OR route. Le ledger est nul hors sonde. */
C55_ORIGIN_RELAX_PROBE <- false;
C55_ORIGIN_RELAX_LEDGER <- null;
/* C48.1 (fiche C48.1) : profil passif des phases internes de
 * OpexIncrementalUpdateProjects. Le ledger reste null hors sonde : le repli 0 n'alloue aucune
 * table et n'atteint ni marqueur d'opcodes ni appel d'API supplementaire. */
C48_INCREMENTAL_PROFILE <- false;
C48_INCREMENTAL_LEDGER <- null;
/* air_fleet_probe : _resizeAirFleets n'emet que ses SUCCES (FG|). Quand une ligne aerienne
 * n'grandit pas, la cause est invisible. FR| donne le premier refus rencontre, une fois par ligne
 * et par an. */
AIR_FLEET_PROBE <- false;
/* Sonde de tension : aucun calcul ni journal supplementaire sur le chemin par defaut. */
TENSION_PROBE <- false;
/* Garde unique du logger de portefeuille : evite un OR supplementaire dans le chemin chaud. */
PORTFOLIO_LOG <- false;
/* fleet_before_new : servir la croissance de flotte avant la construction de lignes aeriennes
 * neuves. Defaut REMIS A 0 le 2026-09-02 apres deux bancs concordants : -20,4 % de profit annuel
 * a 3 ans (t = -3,53) et -18,3 % de valeur a 10 ans (t = -3,81, 5/15 graines, p = 0,041).
 * Pour l'aerien, la LARGEUR bat la PROFONDEUR : une liaison neuve ouvre un flux entier, un avion
 * de plus n'ajoute qu'une tranche marginale. Le reglage reste comme instrument. */
FLEET_BEFORE_NEW <- false;
/* Construction dediee de rabattages vers les hubs (docs/taches.md C1). */
FEEDER_ENABLED <- true;
/* Les aeroports neufs recoivent deja leurs arrets de bus joints dans leur ville
 * (`AIR_JOINED_STOPS`), sans vehicule ni correspondance. Les anciens candidats ville->hub
 * restent disponibles seulement pour rejouer leur strategie au banc ; ils sont exclus par
 * defaut du vivier et de sa regeneration incrementale. */
FEEDER_CANDIDATES_ENABLED <- false;
/* C32 : rabattement arbitre au portefeuille (1) au lieu de la tache dediee (0). */
FEEDER_PORTFOLIO <- true;
/* C45 : persistance complete de l'etat de decision. Defaut aligne sur info.nut (custom_value = 1),
 * adopte au banc officiel 20x10 apparie -- les vingt graines identiques au bit pres. */
SAVE_FULL_STATE <- true;
/* C34.1 : construction aerienne arbitree par le portefeuille seul (1) au lieu de la tache dediee. */
AIR_PORTFOLIO <- true;
/* C34.2 : croissance de flotte aerienne arbitree par le portefeuille (1) au lieu de la tache dediee. */
FLEET_PORTFOLIO <- true;
/* C32 : bonus forfaitaires de classement (fret x1,89, feeder x1,60). 0 = supprimes. */
FLAT_BONUS <- false;
/* Devis réel par AITestMode + AIAccounting avant engagement (docs/taches.md C7). */
RAIL_DEVIS <- true;
/* Expansion marginale : bras A/B inerte par defaut jusqu'au verdict du banc. */
RAIL_EXPAND <- false;
const RAIL_EXPAND_STREAK = 2;
const RAIL_EXPAND_UTIL_PERMILLE = 850;
const RAIL_EXPAND_TIMEOUT_DAYS = 120;
OPS_PER_TICK <- 10000;
_budgetSignIds <- {};
function OpexSign(anchor, name)
{
  if (!DEBUG_SIGNS) return;
  AISign.BuildSign(anchor, name);
}

_currentTaskName <- null;
_currentTaskLogged <- false;

function OpexDecide(kind, fields)
{
  local date = AIDate.GetCurrentDate();
  if (_currentTaskName != null && !_currentTaskLogged && kind != "TASK") {
    _currentTaskLogged = true;
    local cur = _currentTaskName;
    _currentTaskName = null;
    OpexDecide("TASK", "name=" + cur);
    _currentTaskName = cur;
  }
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

/* C39.0 : le journal de la sonde est indépendant de DECISION_LOG. Ce dernier instrumente toute
 * l'IA et change son budget d'opcodes ; C39 doit pouvoir observer le seul routeur passif. */
function OpexC39Log(kind, fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

/* C41.11 reste lisible sans activer le bus C39 : il mesure le scheduler historique lui-meme. */
function OpexC41SchedulerLog(kind, fields)
{
  if (!C41_SLACK_LEDGER && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

/* C41.46 : sonde independante de la famille C41.11/13/14 -- son propre gate, comme les sondes
 * rail-lost ci-dessous. OpexC41SchedulerLog aurait silencieusement avale ces lignes tant qu'aucun
 * des trois autres flags n'est actif (piege trouve au premier smoke test). */
function OpexC41RailSliceLog(fields)
{
  if (!C41_RAIL_SLICE_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_SLICE_LEDGER " + fields);
}

/* C48 : gate dedie, independant de C39/C41. Une sonde armee seule ne doit jamais etre absorbee
 * par le flag d'une autre fiche. */
function OpexC48ProjectAttemptLog(fields)
{
  if (!C48_PROJECT_ATTEMPT_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C48_PROJECT_ATTEMPT " + fields);
}

/* C49 : gate dedie. Ne jamais reutiliser celui de C48/C39/C41 : armer seulement cette sonde
 * doit suffire a publier ses lignes. */
function OpexC49ScarcityLog(fields)
{
  if (!C49_SCARCITY_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C49_SCARCITY " + fields);
}

/* C55 : gate dedie et autonome. Ne jamais reutiliser le gate C49 : la sonde doit publier seule. */
function OpexC55OriginRelaxLog(fields)
{
  if (!C55_ORIGIN_RELAX_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C55_ORIGIN_RELAX " + fields);
}

/* Observe une paire au point meme ou le filtre d'origine route la voit. Cette fonction ne
 * retourne rien et n'ecrit que le ledger de sonde ; elle ne participe a aucun predicat. */
function OpexC55OriginRelaxObserve(kind, lines, src, dst, srcServed, dstServed)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  C55_ORIGIN_RELAX_LEDGER.candidates_seen++;
  if (!srcServed && !dstServed) return;
  C55_ORIGIN_RELAX_LEDGER.rejected_total++;
  if (srcServed && dstServed) {
    C55_ORIGIN_RELAX_LEDGER.both_served++;
    return;
  }
  C55_ORIGIN_RELAX_LEDGER.one_served++;
  if (kind == "pax") C55_ORIGIN_RELAX_LEDGER.one_served_pax++;
  else C55_ORIGIN_RELAX_LEDGER.one_served_freight++;
  /* Cle disponible ici : meme paire geometrique, dans un sens ou dans l'autre, a moins de
   * ORIGIN_SEPARATION des deux originA/originB d'une ligne route existante. */
  if (OpexRoadPairServed(lines, src, dst)) C55_ORIGIN_RELAX_LEDGER.duplicate_exact++;
}

function OpexC49VehicleType(mode)
{
  if (mode == "rail") return AIVehicle.VT_RAIL;
  if (mode == "road") return AIVehicle.VT_ROAD;
  if (mode == "air" || mode == "fleet") return AIVehicle.VT_AIR;
  if (mode == "water") return AIVehicle.VT_WATER;
  return -1;
}

function OpexC49IsMapFailure(passDiscards, rank)
{
  foreach (discard in passDiscards) {
    if (discard.rank != rank) continue;
    if (discard.reason == "build_failed" || discard.reason == "plan_failed"
        || discard.reason == "too_close" || discard.reason == "too_close_hard"
        || discard.reason == "too_close_no_join") return true;
  }
  return false;
}

/* C48.1 : gate dedie. Ne jamais reutiliser celui des tentatives C48 : une sonde armee seule
 * doit publier ses propres lignes. */
function OpexC48IncrementalLog(fields)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C48_INCREMENTAL " + fields);
}

/* C41.47 : un evenement par liberation, pas un accumulateur annuel -- les liberations sont
 * rares (motif observe : quelques par partie), la mesure interessante est LEQUEL candidat et
 * QUAND, pas un total. */
function OpexC41RailCashReleaseLog(fields)
{
  if (!C41_RAIL_CASH_RELEASE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_CASH_RELEASE " + fields);
}

/* C41.48 : un evenement par frontiere de tranche -- la frequence de declenchement EST la
 * mesure (repond a "sur combien de frontieres le test C41.49 aurait-il seulement l'occasion
 * de s'appliquer ?"), donc pas d'agregat qui la masquerait. */
function OpexC41RailDominationLog(fields)
{
  if (!C41_RAIL_DOMINATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_DOMINATION_PROBE " + fields);
}

/* C41.49 : son propre gate, comme C41.46/C41.47/C41.48 -- OpexC41SchedulerLog et
 * OpexC41RailDominationLog l'auraient sinon silencieusement avale (piege deja trouve trois fois). */
function OpexC41ProjectsFallthroughLog(fields)
{
  if (!C41_PROJECTS_FALLTHROUGH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_PROJECTS_FALLTHROUGH_PROBE " + fields);
}

/* C39.5 : gate propre -- ne jamais reutiliser celui d'une autre sonde, sinon armer seulement
 * c39_projects_cadence_probe rendrait le canal silencieux. */
function OpexC39ProjectsCadenceLog(fields)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PROJECTS_CADENCE " + fields);
}

/* C39.6 : gate propre, INDEPENDANT de C39_PROJECTS_CADENCE_PROBE et de C41_RAIL_SLICE_LEDGER --
 * ne jamais reutiliser le gate d'une autre sonde (piege deja trouve trois fois dans ce depot :
 * un canal reutilise reste silencieux tant que SA propre variante n'est pas armee). */
function OpexC39PassClockLog(fields)
{
  if (!C39_PASS_CLOCK_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PASS_CLOCK " + fields);
}

function OpexC41StalenessLog(kind, fields)
{
  if (!C41_STALENESS_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

/* Contrat C41.14 : le hint est une borne prudente d'admission, pas une moyenne ni un budget
 * reservé. Le scheduler ne le lit pas encore pour executer : cette phase mesure seulement si le
 * point d'entree cible pourrait tenir dans le reliquat du tick courant. */
function OpexC41MicrotaskOpsHint(layer)
{
  if (layer == "catalog.water") return 350;
  return -1;
}

/* C41.4 reste observable sans armer C39 : c'est un inventaire de l'evenement, pas une
 * invalidation de catalogue. */
function OpexC41VehicleLostLog(fields)
{
  if (!C41_VEHICLE_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_VEHICLE_LOST " + fields);
}

function OpexC41RailLostLog(fields)
{
  if (!C41_RAIL_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST " + fields);
}

/* Gate C54 autonome : AIDate et AILog ne sont atteignables que si le reglage C54 est actif. */
function OpexC54VehicleOrdersLog(fields)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C54_VEHICLE_ORDERS " + fields);
}

function OpexC41RailLostTopologyLog(fields)
{
  if (!C41_RAIL_LOST_TOPOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_TOPOLOGY " + fields);
}

function OpexC41RailLostPhysicalLog(fields)
{
  if (!C41_RAIL_LOST_PHYSICAL_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_PHYSICAL " + fields);
}

function OpexC41RailSignalRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_SIGNAL_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

function OpexC41RailLostConnectivityLog(fields)
{
  if (!C41_RAIL_LOST_CONNECTIVITY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_CONNECTIVITY " + fields);
}

function OpexC41RailJunctionRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_JUNCTION_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

function OpexC41RailApproachLead(platform, fallbackExit = null)
{
  if (platform == null) return null;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  if (exit == null) return null;
  if ("lead" in platform) return platform.lead;
  if (("anchor" in platform) && ("step" in platform) && ("length" in platform)) {
    return exit == platform.anchor ? exit - platform.step : exit + platform.step;
  }
  return null;
}

/* Un fait local par quai : la voie de sortie existe-t-elle, combien de branches porte-t-elle,
 * et quel signal regarde le quai ? -1 signifie que l'approche ne peut pas etre lue. */
function OpexC41RailApproachFacts(platform, fallbackExit = null)
{
  local facts = { rail = 0, tracks = 0, signal = -1 };
  if (platform == null) return facts;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  if (exit == null) return facts;
  local lead = OpexC41RailApproachLead(platform, fallbackExit);
  /* Les plateformes secondaires anciennes enregistrent ancre/pas/longueur mais pas lead.
   * stationA2/B2 est leur sortie persistée : on reconstitue exactement le voisin immediat,
   * sans explorer la carte. */
  if (lead == null) return facts;
  if (!AIMap.IsValidTile(lead) || !AIMap.IsValidTile(exit) || AIMap.DistanceManhattan(lead, exit) != 1) return facts;
  facts.rail = AIRail.IsRailTile(lead) ? 1 : 0;
  if (!facts.rail) return facts;
  facts.tracks = OpexTileTrackCount(lead);
  facts.signal = AIRail.GetSignalType(lead, exit);
  return facts;
}

/* C41.8 : PBS seulement. Une approche a deux branches est un aiguillage : le moteur refuse
 * souvent d'y poser un signal et C41.7 ne permet pas encore d'en choisir une branche sure.
 * 2=deja PBS, 1=pose, 0=refus, -1=emplacement non eligible, -2=signal non-PBS existant. */
function OpexC41BuildPbsAtApproach(platform, fallbackExit = null)
{
  if (platform == null) return -1;
  local exit = ("station_exit" in platform) ? platform.station_exit : fallbackExit;
  local lead = OpexC41RailApproachLead(platform, fallbackExit);
  if (exit == null || lead == null || !AIMap.IsValidTile(exit) || !AIMap.IsValidTile(lead) ||
      AIMap.DistanceManhattan(lead, exit) != 1 || !AIRail.IsRailTile(lead) ||
      AIRail.IsRailStationTile(lead) || AIRail.IsRailDepotTile(lead) || OpexTileTrackCount(lead) != 1) return -1;
  local type = AIRail.GetSignalType(lead, exit);
  if (type == AIRail.SIGNALTYPE_PBS) return 2;
  if (type != AIRail.SIGNALTYPE_NONE) return -2;
  return AIRail.BuildSignal(lead, exit, AIRail.SIGNALTYPE_PBS) ? 1 : 0;
}

function OpexC41RailDepotFrontFacts(depot)
{
  local facts = { rail = 0, tracks = 0 };
  if (!AIMap.IsValidTile(depot) || !AIRail.IsRailDepotTile(depot)) return facts;
  local front = AIRail.GetRailDepotFrontTile(depot);
  if (!AIMap.IsValidTile(front)) return facts;
  facts.rail = AIRail.IsRailTile(front) ? 1 : 0;
  if (facts.rail) facts.tracks = OpexTileTrackCount(front);
  return facts;
}

/* Compte au plus les quatre voisins contigus. Si `exclude` est fourni (sortie de quai ou depot),
 * `links` est le nombre de branches que le moteur reconnait reellement reliees de l'autre cote de
 * la tuile centrale. Ce n'est pas un pathfinding global. */
function OpexC41RailLocalLinks(center, exclude = null)
{
  local facts = { rail = 0, branches = 0, links = -1 };
  /* C41.10 : AIMap.IsValidTile leve une erreur Squirrel sur `null` au lieu de rendre faux --
   * crash reproduit le 2026-09-08 (ligne sans platformA2/B2 emettant VehicleLost, leadA2 null
   * passe ici depuis le sondage C41.9 dans _processEvents). Garde ajoutee, aucun changement pour
   * un center non-null : le comportement pour toute tuile valide est inchange. */
  if (center == null || !AIMap.IsValidTile(center) || !AIRail.IsRailTile(center)) return facts;
  facts.rail = 1;
  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local offsets = [xStep, -xStep, yStep, -yStep];
  if (exclude != null && AIMap.IsValidTile(exclude) && AIMap.DistanceManhattan(exclude, center) == 1) facts.links = 0;
  foreach (offset in offsets) {
    local neighbor = center + offset;
    if (!AIMap.IsValidTile(neighbor) || AIMap.DistanceManhattan(center, neighbor) != 1 || !AIRail.IsRailTile(neighbor)) continue;
    facts.branches++;
    if (facts.links >= 0 && neighbor != exclude && AIRail.AreTilesConnected(exclude, center, neighbor)) facts.links++;
  }
  return facts;
}

/* C41.10 : repare le seul raccord manquant trouve par C41.9 -- PAS n'importe quelle branche non
 * reconnue, seulement le cas ou l'approche n'a RECONNU AUCUNE branche sortante du tout
 * (OpexC41RailLocalLinks(center, exclude).links == 0), exactement le critere de C41.9. Verifie
 * au smoke le 2026-09-08 : un premier essai qui acceptait toute branche non connectee, meme aux
 * cotes de branches deja reconnues (links >= 1), s'est revele reparer des jonctions hors du
 * perimetre du constat C41.9 (a2/b2/depot avec links=1 ou 2, jamais 0) des le premier VehicleLost
 * rencontre -- au-dela de « ce seul raccord », contrairement a la consigne. Corrige avant tout
 * autre test.
 *
 * Uniquement si UNE seule branche est candidate. Meme prudence que C41.8 pour les aiguillages a
 * plusieurs branches, ou C41.7 ne permet pas encore de choisir une sortie sure : 0 ou plusieurs
 * candidats n'est jamais tente. D'abord AITestMode (le meme AIRail.BuildRail que le reel, sans le
 * payer ni modifier la carte) ; commande reelle seulement si ce test reussit. AreTilesConnected
 * est revérifié APRES la pose reelle : une commande acceptee par le moteur ne garantit pas la
 * connexion recherchee (une piece compatible mais differente peut satisfaire BuildRail).
 * -3 = position illisible (tuiles invalides, pas adjacentes, ou centre non-rail).
 * -2 = links != 0 (hors perimetre C41.9), ou 0/plusieurs branches candidates (rien a faire, ou
 *      ambigu -- jamais tente).
 *  0 = AITestMode refuse la pose.
 *  1 = pose reelle et connexion confirmees.
 *  2 = pose reelle acceptee mais connexion toujours absente (a investiguer). */
function OpexC41RepairJunction(center, exclude)
{
  if (center == null || exclude == null || !AIMap.IsValidTile(center) || !AIMap.IsValidTile(exclude)
      || AIMap.DistanceManhattan(exclude, center) != 1 || !AIRail.IsRailTile(center)) return -3;
  local facts = OpexC41RailLocalLinks(center, exclude);
  if (facts.links != 0) return -2;
  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local offsets = [xStep, -xStep, yStep, -yStep];
  local candidate = null;
  local nCandidates = 0;
  foreach (offset in offsets) {
    local neighbor = center + offset;
    if (!AIMap.IsValidTile(neighbor) || AIMap.DistanceManhattan(center, neighbor) != 1 ||
        neighbor == exclude || !AIRail.IsRailTile(neighbor)) continue;
    nCandidates++;
    candidate = neighbor;
  }
  if (nCandidates != 1) return -2;
  local testOk = false;
  {
    local testMode = AITestMode();
    testOk = AIRail.BuildRail(exclude, center, candidate);
  }
  if (!testOk) return 0;
  if (!AIRail.BuildRail(exclude, center, candidate)) return 0;
  return AIRail.AreTilesConnected(exclude, center, candidate) ? 1 : 2;
}

/* C41.4/C41.5 : l'attribution ne consulte que l'identite deja persistee par la ligne.
 * Elle ne reconstruit pas un voisinage de gares et ne modifie jamais la table retournee. */
function OpexC41PersistedLineForVehicle(lines, vehicle)
{
  if (lines == null) return null;
  foreach (line in lines) {
    if (line == null || !("vehicles" in line) || line.vehicles == null) continue;
    foreach (knownVehicle in line.vehicles) if (knownVehicle == vehicle) return line;
  }
  return null;
}

function OpexC39ProjectSignature(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return "none";
  }
  local project = projects.best[0];
  return project.mode + ":" + project.src + ":" + project.dst;
}

function OpexC41RevisionSnapshot(revisions)
{
  return "c=" + revisions.catalog.cargos + "," + revisions.catalog.towns + ","
         + revisions.catalog.industries + "," + revisions.catalog.rail + ","
         + revisions.catalog.road + "," + revisions.catalog.air + ","
         + revisions.catalog.water + " d=" + revisions.candidates.rail + ","
         + revisions.candidates.road + "," + revisions.candidates.air + ","
         + revisions.candidates.water + " p=" + revisions.portfolio + " s="
         + revisions.selection;
}

/* Le moteur a-t-il survécu au filtre propre à son mode ? Ce n'est pas une décision de
 * construction : C39.3 mesure précisément si le catalogue aurait une raison de propager l'event. */
function OpexC39CatalogUsesEngine(catalog, engine, mode)
{
  if (catalog == null) return false;
  if (mode == "rail") {
    if (catalog.railLocos != null) foreach (loco in catalog.railLocos) if (loco.id == engine) return true;
    if (catalog.wagonByCargo != null) foreach (cargo, wagon in catalog.wagonByCargo) if (wagon.id == engine) return true;
  } else if (mode == "road") {
    if (catalog.roadEngineByCargo != null) foreach (cargo, vehicle in catalog.roadEngineByCargo) if (vehicle.id == engine) return true;
  } else if (mode == "air") {
    if (catalog.plane != null && catalog.plane.id == engine) return true;
    if (catalog.airCombos != null) foreach (combo in catalog.airCombos) if (combo.plane.id == engine) return true;
  } else if (mode == "water") {
    if (catalog.ships != null) foreach (ship in catalog.ships) if (ship.id == engine) return true;
  }
  return false;
}

/* `retained=0` air signifie seulement que le moteur n'est pas le gagnant de `airCombos`.
 * Cette sonde separe les filtres eliminatoires de la domination capacite/vitesse, sans modifier
 * l'algorithme de selection. */
function OpexC39AirEngineReason(catalog, engine)
{
  if (catalog == null || !AIEngine.IsValidEngine(engine)) return "invalid";
  if (!AIEngine.IsBuildable(engine)) return "not_buildable";
  if (catalog.paxCargo < 0 || !AIEngine.CanRefitCargo(engine, catalog.paxCargo)) return "no_pax_refit";
  local planeType = AIEngine.GetPlaneType(engine);
  if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) return "unsupported_type";
  if (AIEngine.GetCapacity(engine) <= 0) return "zero_capacity";
  if (OpexC39CatalogUsesEngine(catalog, engine, "air")) return "selected";
  return "dominated";
}

/* Reserve de tresorerie dynamique : adaptee a la taille de la flotte pour liberer le capital
 * des les premieres annees (15 000 £ au lieu de 50 000 £) et eviter les soldes oisifs. */
DYNAMIC_CASH_RESERVE <- true;
/* Decision utilisateur : la reserve ne doit jamais depasser UN mois d'entretien (totalRunning / 12),
 * contre jusqu'a 3 mois (quarterlyBuffer) ou un forfait fixe selon la branche. Defaut a false pour
 * ne rien changer tant que le banc n'a pas tranche -- voir OpexCashReserve() plus bas. */
RESERVE_MAINT_CAP <- false;
/* Marges de tresorerie exigees EN PLUS de la reserve, sur le chemin aerien. Decision utilisateur
 * du 2026-09-03, tirée du diagnostic 1v1 (results/diag_1v1_decisions.json) : la marge de 30 000 £ est
 * d'un ordre de grandeur au-dessus de la reserve (~7 000 £), donc c'est elle qui gate reellement.
 *   refleet (croissance d'une ligne existante) : 2 000 -> 0, il n'y a rien a couvrir ;
 *   2 aeroports neufs : 30 000 -> 15 000 (valeur demandee) ;
 *   1 aeroport neuf   : 12 000 -> 6 000 (moitie, pour que les paliers restent ordonnes : 15 000
 *                       pour deux aeroports contre 12 000 pour un seul n'aurait plus de sens) ;
 *   0 aeroport neuf (les deux reutilises) : 2 000 -> 0, ce n'est pas une construction.
 * Defaut a false tant que le banc n'a pas tranche, et reglage SEPARE de reserve_maint_cap pour
 * que la mesure puisse attribuer -- c'est la lecon du lot de treize corrections groupees. */
AIR_MARGIN_V2 <- false;
/* C13 : le sac a dos maximise la somme des revenueAnnual (projects.nut:302), donc il ignore
 * entierement les frais de roulement -- deux projets a revenu egal lui sont equivalents meme si
 * l'un paie deux fois plus. profitAnnual et roi existent DEJA sur chaque projet, simplement jamais
 * consultes par l'optimiseur ; et le meme defaut avait ete corrige un etage plus bas
 * (economy.nut:261) sans qu'on remonte d'un cran. 1 = objectif ET ordre de branchement en profit.
 * Consequence attendue, mesuree par le banc : donner plus de capital cesse de degrader le choix
 * (docs/taches.md S0 undecies septies). */
/* G1 : le chemin historique reste disponible pour les comparaisons, mais ne doit plus etre
 * le comportement courant : il maximise le revenu au lieu du profit. Le portefeuille v2 est
 * le defaut et n'appelle pas le sac a dos ; cette valeur protege aussi tout retour explicite
 * au solveur historique. */
KNAPSACK_ROI <- true;
/* docs/taches.md S0 undecies nonies (2026-09-03) : le vivier est rempli sans test de
 * financabilite, sur budgetScore seul (une DENSITE). L'aerien y occupait 43 % des 128 places pour
 * 0 selection en 16 ans -- structurellement trop cher pour tout capitalBudget observe (~131 000 £
 * contre 30-92 000 £). 1 = filtrer l'admission au vivier sur le plafond de capital mobilisable
 * jamais observe, AVANT troncature a PROJECT_POOL_K ; 0 = comportement precedent (classement par
 * densite seule).
 *
 * ADOPTE le 2026-09-03 par decision utilisateur MALGRE un banc d'isolation NEUTRE (20 graines x
 * 3 ans) : company_value +8,1 % et profit_year +11,7 % ne franchissent pas le plancher de
 * detection (t=1,48 et 1,52), et median_station_rating perd significativement au test des signes
 * (5/20, p=0,041). Rien n'est casse -- le gain de valeur n'est simplement pas encore prouve. */
POOL_FINANCEABLE <- true;
/* P1 : repli empirique temporaire du filtre de finançabilité. Le ×1,7 rail
 * est consigné sans artefact source encore présent ; P1.1 doit le remplacer
 * par un devis physique avant élection. Les autres modes restent à 1,0. */
CAPITAL_CALIBRATION <- true;
/* P1.1 : devis physique anticipé, rejeté à −30,7 % sur le diagnostic apparié
 * 5×6. Gardé uniquement comme contrôle expérimental de P1.3. */
RAIL_PREQUOTE <- false;
/* P1.3 volet 1 : conserve le plan de P1.1 puis le revalide au chantier.
 * Experimental et inerte tant que rail_prequote=0. */
RAIL_PREQUOTE_KEEP_PLAN <- false;
/* P1.2 : sonde de terrain en lecture seule (docs/taches.md), aucune decision live. */
RAIL_TERRAIN_PROBE <- false;
const RAIL_PREQUOTE_MAX_CANDIDATES = 2;
const RAIL_PREQUOTE_HARD_CAP = 2500;
/* P4 : n'exclut de la memoire d'abandon que les refus transitoires de caisse
 * (CASH / ERR_NOT_ENOUGH_CASH) survenus apres le garde du portefeuille. Reglage
 * ajoute le 2026-09-08 uniquement pour isoler P4 au banc factoriel P1xP3xP4 sans
 * dupliquer d'arbre Git ; 0 reproduit le comportement historique pre-P4. */
ABANDON_MEMORY_TRANSIENT_GUARD <- true;
/* docs/taches.md S3 undecies (2026-09-03) : les lignes aeriennes rangent des TUILES d'aeroport
 * dans stationA/stationB, mais le code de hub de builder_air.nut les lisait comme des StationID.
 * Consequence mesuree graine 42 : la garde `alreadyConnected` toujours fausse -> NEUF liaisons sur
 * la meme paire de villes en 3 ans, plafond maxRoutes inoperant, et decote de saturation
 * `/(routes+1)` toujours divisee par 1. 1 = resolution correcte tuile -> StationID ;
 * 0 = comportement casse d'avant le 2026-09-03, pour que le banc puisse chiffrer l'ecart. */
AIR_HUB_FIX <- true;
/* Plafonds de demande separes pour garder un banc factoriel : croissance et plan. */
AIR_DEMAND_CAP <- false;
AIR_DEMAND_PLAN <- false;
/* C15 : cadence minimale d'agrandissement de flotte en jours (7 = hebdomadaire, 365 = defaut annuel historique). */
AIR_FLEET_CADENCE_DAYS <- 7;
/* C14 : tampon de cargo au sol pour achat proportionnel (-1 = inactif/defaut). */
AIR_FLEET_BUFFER <- -1;
PAX_FULL_LOAD <- true;
AIR_FULL_LOAD <- false;
COMPLEX_CARGO <- true;
/* Bras experimental : reutiliser un aeroport rentable pour une nouvelle destination. */
AIR_HUB <- true;
RAIL_REFLEET <- true;
/* E10 : Correctif du doublement de flotte routiere au cycle de construction */
ROAD_FLEET_FIX <- true;
/* C26a : Pricer l'avion de la ligne lors du refleet au lieu du meilleur avion du catalogue */
AIR_FLEET_LINE_PRICE <- true;
/* C16 : Plafond physique de flotte aerienne derive de la cadence d'absorption de la piste */
AIR_CADENCE_CAP <- true;
/* C26b : Correctif du faux embouteillage lorsque le vehicule est a l'arret a quai en chargement
 * Mesure a 10 ans et 3 ans : DEGRADE le profit de -17,6 % s'il n'est pas couple a MARGINAL_FLEET,
 * car il empile jusqu'a 16 camions sur des arrets a 1 seul quai. Defaut a false. */
ROAD_LOADING_FIX <- false;
/* A7.2 : Vente immediate des convois au depot via ET_VEHICLE_WAITING_IN_DEPOT */
EVENT_DEPOT_SELL <- false;
/* A7.1 : Stop-loss immediat sur fermeture d'industrie via ET_INDUSTRY_CLOSE */
EVENT_INDUSTRY_CLOSE <- false;
/* A7.3 / C17 : Sonde subventions en lecture seule via AIEventSubsidy* */
EVENT_SUBSIDY_PROBE <- false;
/* A7.4 : Alerte et diagnostic convois perdus/bloques via ET_VEHICLE_LOST */
EVENT_VEHICLE_LOST <- false;
/* P3 / A7.5 : une nouvelle ville ou industrie rend le portefeuille obsolete.
 * Le rafraichissement reactif est rare et evite d'attendre le prochain mois. */
EVENT_CATALOG_INVALIDATE <- true;
const CASH_RESERVE_STATIC = 25000;
const CASH_RESERVE_MIN = 5000;
const CASH_RESERVE_MAX = 25000;
/* C43/E3 famille 2 : CASH_RESERVE_MIN mord-il ? OpexCashReserve() est appelee tres souvent (a
 * chaque decision de construction), donc journaliser chaque appel serait bruyant -- compteurs
 * cumulatifs, publies une fois par an en delta par la tache "report". */
CASH_RESERVE_PROBE <- false;
CASH_RESERVE_PROBE_CALLS <- 0;
CASH_RESERVE_PROBE_MIN_BINDS <- 0;
CASH_RESERVE_PROBE_MAX_BINDS <- 0;

function OpexCashReserveProbeLog(fields)
{
  if (!CASH_RESERVE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " CASH_RESERVE_PROBE " + fields);
}

function OpexCashReserve()
{
  if (!DYNAMIC_CASH_RESERVE) {
    /* Branche statique : la boucle vehicules n'existe ici que si le plafond est demande, jamais
     * inconditionnellement (elle serait sans objet a reglage 0). */
    if (!RESERVE_MAINT_CAP) return CASH_RESERVE_STATIC;
    local totalRunning = 0;
    local vehicles = AIVehicleList();
    vehicles.Valuate(AIVehicle.GetRunningCost);
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
      totalRunning += vehicles.GetValue(v);
    }
    local maintCap = totalRunning / 12;
    if (maintCap < CASH_RESERVE_STATIC) return maintCap;
    return CASH_RESERVE_STATIC;
  }
  local totalRunning = 0;
  local vehicles = AIVehicleList();
  vehicles.Valuate(AIVehicle.GetRunningCost);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    totalRunning += vehicles.GetValue(v);
  }
  local reserve;
  local quarterlyBuffer = totalRunning / 4;
  if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_CALLS++;
  if (quarterlyBuffer < CASH_RESERVE_MIN) {
    reserve = CASH_RESERVE_MIN;
    if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_MIN_BINDS++;
  } else if (quarterlyBuffer > CASH_RESERVE_MAX) {
    reserve = CASH_RESERVE_MAX;
    if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_MAX_BINDS++;
  } else reserve = quarterlyBuffer;
  /* Le plafond d'un mois d'entretien (decision utilisateur) prime sur le plancher CASH_RESERVE_MIN :
   * totalRunning / 12 est toujours < totalRunning / 4, donc ce plafond mord des que l'entretien
   * annuel passe sous 60 000 £, y compris jusqu'a 0 flotte vide. Assume, pas une marge de securite. */
  if (RESERVE_MAINT_CAP) {
    local maintCap = totalRunning / 12;
    if (maintCap < reserve) reserve = maintCap;
  }
  return reserve;
}

/* Capital effectivement mobilisable par le portefeuille. Cette valeur doit toujours etre relue
 * apres une depense : la caisse, le reliquat d'emprunt et la reserve peuvent tous avoir change.
 * Centraliser la formule evite que la future passe dynamique (C38) ne diverge de la generation,
 * du rafraichissement ou du cache incremental. */
function OpexAvailableCapital()
{
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local borrowable = REBORROW
      ? AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount() : 0;
  if (borrowable < 0) borrowable = 0;
  local available = cash + borrowable - OpexCashReserve();
  return available > 0 ? available : 0;
}

/* Plafond absolu du pathfinder. Initialisation de repli seulement : Start() le remplace UNE fois
 * par pathfinder_hard_cap_k. Plafonné à 10 000 (docs/taches.md A3, §0 undecies ter) pour
 * éliminer le gel de l'IA pendant des mois sur les recherches chères. */
HARD_ITERATION_CAP <- 10000;

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

/* Le classement ne contient que TOP_K = 20 candidats. Le plafond de continuation est exactement
 * cette borne existante, pas un second seuil arbitraire : une annee sans argent examine au plus
 * 20 candidats, donc au plus 20 appels de solde et de _tooClose, sans lancer A* avant le test de
 * cash. L'ancien break en examinait 1 ; parcourir les 19 restants est le cout borne qui rend enfin
 * visible un candidat moins rentable par iteration mais financable en capital. */
TOP_K <- 20;
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
ROAD_MAX_NEW_LINES_PER_YEAR <- 36;
ROAD_MAX_ATTEMPTS_PER_YEAR <- 60;

/* Seuil de remboursement d'emprunt : sous ce plancher de tresorerie on ne rembourse pas, un
 * emprunt a 5 % coute bien moins qu'une ligne manquee faute de cash. Au-dessus, l'argent qui
 * dort ne rapporte rien -- autant reduire l'emprunt.
 *
 * Devenu reglable le 2026-08-29 pour que le banc puisse l'opposer a lui-meme en une seule
 * campagne, puis abaisse de 1 000 000 a 300 000 apres verdict de ce banc. La valeur ci-dessous
 * n'est qu'un repli : Start() la remplace par le reglage. Tout le raisonnement, la mesure qui
 * condamne l'ancienne valeur et le verdict sont dans info.nut. */
LOAN_REPAY_FLOOR <- 300000;

/* Recherche de chemin ferroviaire reprenable d'un tour de file a l'autre (docs/taches.md A4).
 * Repli FAUX : le defaut conserve la boucle bloquante mesuree (7 mois sans action, graine 100,
 * juin-dec 1971). 1 decoupe l'A* en tranches de RAIL_SEARCH_SLICE, rend la main a
 * _runNextTask, et reprend le meme pathfinder au tour suivant. Change l'entrelacement donc
 * les decisions : le banc tranchera. */
RAIL_SEARCH_RESUMABLE <- false;
/* C20 : Echeance de securite locale par micro-etape (tranche) au lieu d'une echeance globale en ticks. */
RAIL_MICRO_DEADLINE <- false;

/* Pathfinding segmente (docs/taches.md A5). Repli VRAI depuis le 2026-09-03 : c'est le
 * defaut du reglage, et le repli doit valoir le defaut pour qu'une partie sans reglage lu
 * se comporte comme une partie normale. 1 porte TrainLineAI::_segmentedPath. Sonde
 * 2026-09-03 : 4/10 tentatives rail en ABND ; A3 plafonne a 10k donc l'enjeu est de
 * convertir les abandons, pas d'accelerer les succes. Le banc dit reseau +13 % pour une
 * valeur neutre (docs/taches.md A5). */
RAIL_SEGMENTED_SEARCH <- true;

/* Journalisation structuree des decisions (decision_log) : repli FAUX. */
DECISION_LOG <- false;
_lastAirRefuseMonth <- -1;
_lastFeederRefuseMonth <- -1;
_lastProjectScanMonth <- -1;

/* La memoire est l'autre correctif, independamment des 40 000 iterations. Elle reste un repli
 * actif jusqu'a la lecture unique de abandon_memory dans Start(), comme les autres reglages de
 * decision qui ne changent pas pendant une partie. */
ABANDON_MEMORY <- true;
/* C33.3 : Cooldown en jours avant réessai d'une paire abandonnée (defaut 365, adopte ; 0 = permanent). */
ABANDON_COOLDOWN_DAYS <- 0;
/* C22 : Filtrer les paires abandonnées dès la génération des candidats (defaut 1, adopte). */
ABANDON_GEN_FILTER <- false;

/* Raccordement de gare : repli actif jusqu'a la lecture unique de station_join dans Start().
 * Commande AUSSI la relaxation d'origine a la generation (candidates.nut) : les deux moities du
 * meme mecanisme partagent un seul reglage, sans quoi le bras de controle du banc ne reproduirait
 * pas le comportement historique. Repli FAUX depuis le 2026-08-29 : deux bancs (vivier, puis
 * post-traction) montrent un effet de construction sans valeur. Tout le verdict est dans info.nut. */
STATION_JOIN <- false;
/* Porte H1 : 0 = pas de plafond (v1 inerte). N = rejeter la jointure si
 * candidate.distance >= N, sans A*. Defaut 0. Valeur de travail 50
 * (results/opex_join_pop.json). Inerte si station_join = 0. */
JOIN_MAX_DISTANCE <- 0;
/* H2 : joindre au lieu, pas en repli _tooClose. Defaut 0. Les candidats
 * naissent d'une gare rail OpexAI vers une origine libre dans 25-75
 * tuiles, avec l'objet join deja attache. Independant de station_join :
 * le banc doit pouvoir attribuer. JOINPATH reste dedie. */
JOIN_PLACE <- false;

/* Filtre d'origine sitable : repli ACTIF jusqu'a la lecture unique de origin_sitable dans
 * Start(). Defaut passe a 1 le 2026-09-09 (decision utilisateur) ; 1 ecarte du TOP_K les
 * sources sans tuile de terre voyant le cargo dans leur bassin. Le classement a 0 reste celui
 * d'avant le filtre, conserve pour l'A/B. */
ORIGIN_SITABLE <- true;

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

/* Drainage du budget d'opcodes du tick (revue du controleur, docs/taches.md S0 sexies point 1) :
 * repli FAUX jusqu'a la lecture unique de loop_budget dans Start(). Defaut 0 : la boucle
 * principale execute exactement UNE tache par tick puis Sleep(1), donc tout ce qui reste des
 * 10 000 opcodes du tick est PERDU -- le budget n'est pas reportable. Sur une partie de 3 ans
 * (~81 000 ticks, ~810 M d'opcodes) c'est le gisement dont AAAHogEx tire ~150 gares quand nous
 * en tirons ~18. Sous 1 : on enchaine les taches tant qu'il reste de quoi travailler.
 * Coherent avec docs/philosophie_armes_egales : Sleep sert aux parties avec des humains, pas
 * face a une IA qui, elle, ne dort pas entre ses chunks. */
LOOP_BUDGET <- false;
/* Marge laissee au moteur pour ne pas suspendre au milieu d'une transaction, et plafond de taches
 * par tick pour qu'un tour de file entierement compose de taches hors periode ne brule pas le
 * budget en pur ordonnancement. */
const LOOP_BUDGET_FLOOR = 2000;
const LOOP_BUDGET_MAX_TASKS = 8;

/* Portefeuille v2 (revue du portefeuille, docs/taches.md S0 sexies et S0 septies) : repli
 * temporaire jusqu'a la lecture unique de portfolio_v2 dans Start(). Defaut 1 : chemin corrige.
 * Sous 1, quatre defauts confirmes tombent ensemble --
 *   - l'election modale par couple O/D se fait APRES le test de capital, pas avant ;
 *   - l'objectif passe du revenu total au PROFIT par livre de capital ;
 *   - le sac a dos 0/1 est remplace par « le meilleur projet finançable », puisque maxBatch = 1
 *     n'en batit qu'un et jetait tout le reste ;
 *   - la contrainte « pas deux projets sur la meme extremite » disparait : elle interdisait la
 *     topologie en etoile de builder_air sans rien apporter a un batch de taille 1.
 * Plus la regeneration du portefeuille des que le capital mobilisable a materiellement grandi,
 * au lieu d'attendre le mois suivant. */
PORTFOLIO_V2 <- true;
/* Taille du batch du portefeuille. Repli 1 jusqu'a la lecture unique de
 * portfolio_max_batch dans Start() : 1 garde le break apres le premier succes, donc le chemin
 * livre reste strictement le meme. */
PORTFOLIO_MAX_BATCH <- 1;
/* C38 : le batch dynamique re-classe le vivier apres chaque succes contre la caisse vivante.
 * Il reste desactive jusqu'au diagnostic puis au banc apparie ; a 0 le chemin livre ne porte
 * aucun etat de batch supplementaire. */
PORTFOLIO_DYNAMIC_BATCH <- false;
const DYNAMIC_BATCH_OPS_FLOOR = 2500;
/* P2 : le bras C38 ne doit pas balayer tout le vivier sur une rafale de refus,
 * ni consommer tout le tick. Ces controles ne sont lus que pour le bras
 * dynamique ; 0 reconstitue respectivement l'ancien balayage et son garde
 * absolu de 2 500 opcodes. */
DYNAMIC_BATCH_REJECT_LIMIT <- 3;
DYNAMIC_BATCH_OPS_BUDGET_PCT <- 50;
/* Gain absolu minimal avant de rejouer la generation : en dessous, le cout en opcodes ne vaut pas
 * la peine d'etre paye pour quelques milliers de livres. */
const PORTFOLIO_REFRESH_MIN_GAIN = 50000;
/* C43/E3 famille 2 : PORTFOLIO_REFRESH_MIN_GAIN mord-il independamment du doublement (l'autre
 * moitie de la condition ET) ? Compteurs cumulatifs, publies en delta annuel par la tache
 * "report", meme schema que CASH_RESERVE_PROBE. */
PORTFOLIO_REFRESH_PROBE <- false;
PORTFOLIO_REFRESH_PROBE_CHECKS <- 0;
PORTFOLIO_REFRESH_PROBE_GAIN_OK <- 0;
PORTFOLIO_REFRESH_PROBE_DOUBLE_OK <- 0;
PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY <- 0;
/* Cout reel d'un OpexCatalog.refresh() sur le code/graines actuels, plutot que de reutiliser la
 * mesure du 2026-08-28 (docs/taches.md C43/E3, [[catalogue_churn_et_cout]]) telle quelle. Mesure
 * autonome (OpexOpsMeasureBegin/End, budget.nut) pour ne pas imbriquer les begin()/end() internes
 * a refresh(), non reentrants. */
PORTFOLIO_REFRESH_PROBE_REFRESH_OPS <- 0;
PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT <- 0;

function OpexPortfolioRefreshProbeLog(fields)
{
  if (!PORTFOLIO_REFRESH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " PORTFOLIO_REFRESH_PROBE " + fields);
}
/* Plancher de profit absolu du portefeuille v2, en POURCENTAGE du meilleur profit finançable du
 * moment. Repli 0 (= tri au seul ratio) jusqu'a la lecture de portfolio_floor_pct dans Start().
 * Voir projects.nut::OpexProjectSelectAffordable pour le mecanisme et la mesure qui l'impose. */
PORTFOLIO_FLOOR_PCT <- 0;

/* A1 (docs/taches.md A1, Option A) : classement du portefeuille par vecteur de tension de Liebig. */
TENSION_SCORING <- false;
TENSION_DECISION_FRICTION <- 0.05;
/* C35.3 (docs/taches.md C35.3) : coût réduit à prix d'ombre dual. */
SHADOW_PRICING <- false;

/* Correctifs de flotte (revue flotte et entretien, docs/taches.md S0 nonies) : repli FAUX jusqu'a
 * la lecture unique de fleet_fix dans Start(). Defaut 0 : chemin historique inchange. Sous 1,
 * deux defauts mesures tombent ensemble --
 *   1. une ligne routiere neuve n'achete plus une seconde flotte complete dans son propre cycle de
 *      construction : `vehCount` n'etant ecrit qu'une fois par an, elle arrivait au refleet avec
 *      have = 0 et se faisait reconstruire, ordres dupliques compris.
 *   2. `isAnyWaiting` ne prend plus un vehicule en chargement pour un embouteillage. Sous
 *      OF_FULL_LOAD_ANY c'est l'etat normal d'un camion, et les trois heuristiques de croissance
 *      exigeant !isAnyWaiting, le signal etait inverse par rapport a son intention.
 *
 * ⚠️ CORRIGE (2026-09-08) : cette liste comptait un 3e point, « rail_refleet redevient
 * ATTEIGNABLE », decrit comme derriere fleet_fix. C'etait deja faux au moment de l'ecrire : le
 * commit 3a15646 (« fix items G1 G7 from code review », 2026-09-07 11:10) a rendu la garde
 * d'entree de _expandRailLines et la tache "expand" INCONDITIONNELLES (voir le commentaire
 * G6§1 sur _expandRailLines) -- rail_refleet est reellement atteignable au defaut livre
 * (rail_expand=0, rail_refleet=1), independamment de fleet_fix. docs/taches.md et le
 * commentaire de la reglage `fleet_fix` (info.nut) repetaient la meme erreur ; corriges le
 * meme jour. Ne pas retirer `rail_refleet` comme code mort (§8 taches.md le proposait par
 * erreur). */
FLEET_FIX <- false;

/* La croissance urbaine cede le pas au portefeuille (docs/taches.md S0 septies et S0 decies) :
 * repli FAUX jusqu'a la lecture unique de growth_yields dans Start(). Defaut 0 : chemin
 * historique inchange -- _tryTownGrowth depense des qu'il a de quoi payer, sur des candidats a
 * profit predit NUL. Sous 1, il exige en plus un surplus couvrant le capital que le portefeuille
 * s'est deja engage a depenser.
 *
 * MESURE le 2026-09-02 (results/bench_growth_yields_3y.json, 20 graines x 3 ans, apparie) : REJETE.
 * company_value +4,8 % pour le controle (t = 1,33, 9/20 : nul), profit_year −0,3 % (nul), mais
 * median_station_rating +10,4 % pour le controle (t = 2,97, 15/20 : REEL et defavorable a la
 * variante), et la graine 2026 s'effondre a company_value = 1. Lecture : le `profitAnnual = 0`
 * porte par les candidats de croissance est un compteur faux, pas une depense gachee -- la ville
 * qui grandit alimente les gares deja construites, et ca se lit sur la note. Ne pas remettre a 1
 * sans corriger d'abord le profit predit de ces candidats. */
GROWTH_YIELDS <- false;

/* Marge d'autorite aerienne appliquee PAR PLAN dans OpexAirEconomics (builder_air.nut) plutot
 * qu'en rabotant maxCapital chez l'appelant. Voir le commentaire de la boucle de dimensionnement
 * (builder_air.nut) pour le raisonnement complet et le banc a -11,5 % qu'il corrige.
 *
 * ADOPTE le 2026-09-02, defaut 1 (results/bench_air_margin_3y.json, 20 graines x 3 ans, apparie) :
 * company_value +1,3 % (t = 0,26), profit_year -1,6 % (t = -0,28), toutes metriques sous t = 1,2.
 * NEUTRE, donc adopte pour la JUSTESSE, pas pour la performance -- ne revendiquer aucun gain. Le
 * defaut vise est reel mais son cout est nul, ce qui est coherent avec loop_budget nul : le gachis
 * d'un cycle d'opcodes ne se paie pas. Repli VRAI jusqu'a la lecture unique dans Start(). */
AIR_MARGIN <- true;

/* _tryBuildAir memorise ses echecs de construction dans _abandonedPairs et OpexAirPlans les
 * ecarte pendant le scan. Sous 0, chemin historique -- l'echec n'est pas retenu, et comme
 * OpexAirPlans ne renvoie qu'un seul bestPlan, le cycle suivant re-scanne tous les sites pour
 * reproposer exactement la meme paire et echouer de la meme facon. Le chemin portefeuille, lui,
 * memorisait deja ses echecs.
 *
 * ADOPTE le 2026-09-02, defaut 1 (results/bench_air_abandon_3y.json, 20 graines x 3 ans, apparie) :
 * company_value +6,1 %, profit_year +6,8 %, profit +4,0 %. Les t restent sous 2 (1,90 / 1,89 /
 * 1,95) mais le TEST DES SIGNES tranche : la variante gagne 18/20, 19/20 et 19/20, soit
 * p = 4e-4 et 4e-5. L'effet est petit et CONSTANT, pas grand et bruyant -- et sur une plateforme
 * deterministe un changement neutre rebat les trajectoires et donne ~10/20. Le plancher de
 * detection a ~15 % vaut pour la comparaison de MOYENNES, pas pour le test des signes.
 * Repli VRAI jusqu'a la lecture unique dans Start(). */
AIR_ABANDON <- true;

/* Correctifs du modele economique (revue de economy.nut, docs/taches.md S0 octies) : repli FAUX
 * jusqu'a la lecture unique de economy_fix dans Start(). Defaut 0 : chemin historique inchange.
 * Sous 1, deux defauts du rendement unitaire tombent --
 *   1. les seuils de note de ramassage passent de 6,8 / 13,5 / 27 / 47 jours aux valeurs du source
 *      du moteur, 7,5 / 15 / 30 / 52,5 (3 / 6 / 12 / 21 cycles a ~2,5 jours le cycle). Chaque
 *      palier etait ~10 % trop strict, et TARGET_HEADWAY_DAYS = 7 tombait entre les deux valeurs du
 *      premier : le modele notait sa propre cible de conception a 95 quand le moteur accorde 130.
 *      L'ancre de calibration suit desormais la tranche reelle de cette cible, pour que le modele
 *      reproduise exactement STATION_RATING_PCT au headway de calibration.
 *   2. le nombre de convois est choisi au profit par livre de capital -- le meme objectif que celui
 *      qui l'arbitrera au portefeuille -- au lieu du profit absolu, qui livrait systematiquement la
 *      variante la plus gourmande en capital. */
ECONOMY_FIX <- true;

/* Correctifs de PRICING (revue de economy.nut, docs/taches.md S0 octies et S0 septies) : repli
 * FAUX jusqu'a la lecture unique de pricing_fix dans Start(). Defaut 0 : chemin historique
 * inchange. Sous 1, trois incoherences de modele tombent, toutes dans l'arbitrage MULTIMODAL --
 * c'est-a-dire la ou le portefeuille compare rail et route sur des nombres qui n'etaient pas
 * calcules de la meme facon :
 *   1. la route applique enfin OpexStationRatingForHeadway, que le rail et l'air utilisent deja.
 *      Elle etait figee a STATION_RATING_PCT = 50 % a plat, donc le meme mecanisme physique --
 *      la frequence fixe la note, donc la part de demande captee -- etait price differemment selon
 *      le mode. Une ligne de bus courte et frequente vaut 65,7 % sous la courbe, pas 50 % ;
 *   2. le capital rail inclut enfin le DEPOT, que builder_rail.nut paie a chaque ligne et que la
 *      route comme l'eau comptent deja. L'omission gonflait le ROI rail face a la route ;
 *   3. l'estimation d'opcodes d'un projet routier ne facture plus ses iterations au tarif du
 *      pathfinder RAIL -- une erreur de dimension qui sous-estimait opcodeScore cote route. */
PRICING_ROAD_RATING <- false;
PRICING_RAIL_DEPOT <- false;
PRICING_ROAD_OPS <- true;

/* Dimensionnement marginal et progressif de flotte (item de tete, 2026-09-01) : repli FAUX
 * jusqu'a la lecture unique de marginal_fleet dans Start(). Defaut 0 : chemin actuel
 * rigoureusement inchange -- MAX_ROAD_VEHICLES/plafond 16 route, clonage immediat a
 * candidate.trains, jusqu'a 4 avions/an air, flotte initiale a 3/6 avions. Mesure au banc apparie
 * 20 graines contre AAAHogEx : 8x moins de vehicules ET 8x moins de gares, plus un rendement par
 * vehicule ajoute -31,4 % (6332 £/an contre 9229 £), avec 3,26 vehicules/gare contre 2,71 --
 * capital immobilise plutot que redeploye en nouvelles lignes. Sous 1 : demarrage MINIMAL (1
 * vehicule/avion), croissance seulement apres profit reel mesure, borne par une contrainte
 * physique/marginale (quais route, age+charge+un avion/an en air) plutot que par une constante
 * generique. Voir economy.nut::OpexRoadPhysicalVehicleCap, builder_road.nut (clonage initial),
 * builder_air.nut::OpexAirEconomics (flotte initiale), main.nut::_refleetRoadLines et
 * _resizeAirFleets (croissance). */
MARGINAL_FLEET <- false;

/* air_roi_order (2026-09-03) : ordre de service de la croissance de flotte aerienne.
 * _resizeAirFleets parcourait _lines dans l'ordre de CONSTRUCTION -- ce n'etait pas une decision
 * de conception, juste l'ordre du tableau. Consequence mesuree (5 graines x 3 ans,
 * results/diag_airfleet_monthly_5s3y.json) : la premiere ligne aerienne ouverte capte la tresorerie
 * a chaque passage, et les autres ne grandissent JAMAIS -- 0 croissance sur 3 graines / 5, et
 * +1 avion par an au mieux ailleurs. Aucun effet compose n'apparait nulle part.
 * 1 (defaut) sert d'abord la ligne au meilleur profit PAR APPAREIL, donc celle qui rembourse
 * l'avion suivant le plus vite ; 0 rend l'ordre historique pour que le banc puisse trancher. */
AIR_ROI_ORDER <- true;

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

/* Croissance urbaine : repli VRAI jusqu'a la lecture unique de town_growth dans Start().
 * Complete avec 5-n stations de bus pour chaque ville desservie comptant n gares/aeroports. */
TOWN_GROWTH_ENABLED <- true;
TOWN_GROWTH_SKIP_NOOP <- false;


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
  /* Catalogue geometrie eau : { cursor, towns = { townId = { sites = [{dock, waterTiles}] } } }.
   * Les entrees sans site sont les negatifs exhaustifs ; voir builder_water.nut. */
  _waterSiteCatalog = null;
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
  _lastAirFleetMonth = -1;
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
  _c48AttemptLedger = null;
  _c48PassLedger = null;
  _c49ScarcityLedger = null;
  _c49ScarcityRegime = "cash";
  _c39CadenceLastDate = null;
  _c39CadenceLastTick = null;
  _c39CadenceLastCycle = null;
  _c39FinanceableSince = null;
  _startYear = -1;
  _vehiclesToScrap = null;
  /* C41.8 : ensemble coalescé par ligne, consommé par une seule micro-tâche. */
  _c41RailSignalLines = null;
  /* C41.10 : même schéma, réparation de raccord au lieu de pose PBS. */
  _c41RailJunctionLines = null;
  _activeSubsidies = null;
  _subsidyStats = null;
  /* G4§1 : drapeau pose par _markPairAbandoned dans _tryBuildProjects, lu en fin de passe
   * pour declencher la reelection incrementale sans dependre de DECISION_LOG. */
  _hadAbandonsThisPass = false;

  constructor()
  {
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
    this._pendingLines = null;
    this._waterSiteCatalog = { cursor = 0, towns = {} };
    this._abandonedPairs = {};
    this._abandonCounts = {};
    this._vehiclesToScrap = {};
    OpexAirResetSiteCache();
    this._activeSubsidies = {};
    this._c41RailSignalLines = {};
    this._c41RailJunctionLines = {};
    this._subsidyStats = { offers = 0, expiredWithoutAward = 0, awardedSelf = 0, awardedOther = 0, matchedPool = 0 };
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
    /* Priorite : donnees et stop-loss, croissance des flottes existantes avant nouveaux projets,
     * portefeuille multimodal ROI, croissance urbaine, dette. */
    this._taskQueue = [
      { name = "catalog", dueCycle = 0, enabled = true },
      /* C41.1 est arme par un EngineAvailable eau ; hors evenement, aucun scan periodique. */
      { name = "c41_water", dueCycle = 2147483647, enabled = false },
      /* C41.15 : meme contrat etroit que l'eau, sans reconstruire les candidats route. */
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
      { name = "feeders", dueCycle = 0, enabled = true },
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
  function _tryBuildFeeders(year);
  function _tryBuildMailFeeder(candidate, paxResult, year);
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
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _scrapDeadLines(year);
  function _triggerScrapLine(line, criterion);
  function _refleetRoadLines(year);
  function _resizeAirFleets(year);
  function _expandRailLines(year);
  function _continueRailExpansion();
  function _startRailSearch(candidate, join, placeJoin, alternativeRatio, hardCap, projectIndex);
  function _continueRailSearch();
  function _consumeRailSearch(year);
  function _recordRailAttempt(candidate, result, join, placeJoin, posPacked, year);
  function _startRailUpgradeSearch(line, prep);
  function _consumeRailUpgrade();
  function _findLineById(lineId);
  function _processEvents();
  function _markDirty(reason, catalogLayers = null, candidateLayers = null,
                      portfolio = false, selection = false, affectedKind = null, affectedId = -1,
                      affectedMode = null, targetedRelevant = true);
  function _logStalenessRefresh(reason);
  function _markPairAbandoned(key);
  function _pruneAbandonedPairs(now);
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

/* P4 : la memoire d'abandon ne doit retenir que les impossibilites durables.
 * Un constructeur peut constater une caisse insuffisante APRES le garde du
 * portefeuille (prix reel, re-emprunt refuse ou cout devenu plus eleve que le
 * devis). Ce refus est transitoire : le memoriser retire injustement la paire
 * du vivier, dans le batch comme sur le chemin unitaire. */
function OpexBuildFailureIsAbandonable(result)
{
  if (result == null) return false;
  if (!ABANDON_MEMORY_TRANSIENT_GUARD) return true;
  if (("reason" in result) && result.reason == "CASH") return false;
  if (("error" in result) && result.error == AIError.ERR_NOT_ENOUGH_CASH) return false;
  return true;
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
/* Un vehicule dessert-il cette gare dans ses ordres ? Sert a distinguer NOS vehicules de ceux
 * d'une ligne voisine quand un StationID est partage. */
function OpexVehicleServesStation(vehicle, stationId)
{
  if (!AIStation.IsValidStation(stationId)) return false;
  local count = AIOrder.GetOrderCount(vehicle);
  for (local i = 0; i < count; i++) {
    if (!AIOrder.IsValidVehicleOrder(vehicle, i)) continue;
    local dest = AIOrder.GetOrderDestination(vehicle, i);
    if (AIStation.GetStationID(dest) == stationId) return true;
  }
  return false;
}

function OpexLineVehicleIds(line, stationId)
{
  if (("mode" in line) && line.mode == "road") {
    /* Le commentaire de _scrapDeadLines jure que la liste vient des vehicules POSES PAR CETTE
     * LIGNE, « PAS une interrogation par gare qui prendrait les convois du voisin sur un
     * StationID partage ». C'etait faux ici, et exactement pour la route : AIVehicleList_Station
     * rend TOUS les vehicules qui desservent la gare, donc ferrailler une ligne morte envoyait au
     * depot et vendait les camions de toutes les lignes co-localisees (docs/taches.md S0 nonies).
     *
     * Les lignes routieres ne portent pas de liste `vehicles` par conception. On filtre donc par
     * les ORDRES : un camion de cette ligne dessert forcement son AUTRE extremite. Un voisin qui
     * ne partage que stationA est ainsi ecarte. Si stationB est inconnue ou invalide, on retombe
     * sur l'ancien comportement plutot que de rendre une liste vide -- ne jamais transformer un
     * defaut de precision en perte de ferraillage. */
    local roadIds = [];
    local other = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
    local filter = AIStation.IsValidStation(other) && other != stationId;
    local roadVehicles = AIVehicleList_Station(stationId);
    for (local v = roadVehicles.Begin(); !roadVehicles.IsEnd(); v = roadVehicles.Next()) {
      if (filter && !OpexVehicleServesStation(v, other)) continue;
      if (("cargo" in line) && line.cargo >= 0 && AIVehicle.GetCapacity(v, line.cargo) <= 0) continue;
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
  if (("isFeeder" in candidate) && candidate.isFeeder) {
    local srcTown = ("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(candidate.src);
    local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
    return "feeder|" + srcTown + "|" + candidate.hubStationId + "|" + slot;
  }
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
    /* G9§1 : Pour du fret vers une ville, GetIndustryID retourne -1 (invalide).
     * La cle devenait freight|cargo|sourceId|-1, partagee par TOUTES les villes du
     * meme producteur/cargo : un seul echec bannissait la famille entiere pendant
     * au moins un an. On utilise dstTown (pose par les generateurs) prefixe "t"
     * pour distinguer ville/industrie sans collision d'identifiants. */
    if (dst < 0 && ("dstTown" in candidate) && candidate.dstTown >= 0) {
      dst = "t" + candidate.dstTown;
    }
    if (src < 0 && ("srcTown" in candidate) && candidate.srcTown >= 0) {
      src = "t" + candidate.srcTown;
    }
  }
  return candidate.kind + "|" + candidate.cargo + "|" + src + "|" + dst;
}

/* C33.3 : Enregistre un échec de construction avec horodatage et compteur d'échecs cumulés. */
function OpexAI::_markPairAbandoned(key)
{
  local now = AIDate.GetCurrentDate();
  local count = (key in this._abandonCounts) ? (this._abandonCounts[key] + 1) : 1;
  this._abandonCounts[key] <- count;
  this._abandonedPairs[key] <- { date = now, count = count };
  /* G4§1 : signaler qu'un abandon a eu lieu dans cette passe. _tryBuildProjects lit ce
   * drapeau pour declencher la reelection incrementale C36.1 apres un echec, sans
   * dependre de passDiscards qui est garde par DECISION_LOG (defaut 0). */
  this._hadAbandonsThisPass = true;
  if (DECISION_LOG) {
    OpexDecide("ABANDON_PAIR", "key=" + key + " count=" + count + " cooldown=" + (ABANDON_COOLDOWN_DAYS * count));
  }
}

/* C33.3 : Purge les paires dont le délai de reprise est écoulé.
 * Délai = ABANDON_COOLDOWN_DAYS * count (plafonné à 5 ans / 1825 jours). */
function OpexAI::_pruneAbandonedPairs(now)
{
  if (ABANDON_COOLDOWN_DAYS <= 0) return;
  local toDelete = [];
  foreach (key, val in this._abandonedPairs) {
    if (typeof val != "table" || !("date" in val)) continue;
    local count = ("count" in val) ? val.count : 1;
    local cooldown = ABANDON_COOLDOWN_DAYS * count;
    if (cooldown > 1825) cooldown = 1825;
    if ((now - val.date) >= cooldown) {
      toDelete.append(key);
    }
  }
  foreach (k in toDelete) {
    delete this._abandonedPairs[k];
  }
  if (toDelete.len() > 0 && DECISION_LOG) {
    OpexDecide("ABANDON_PRUNE", "count=" + toDelete.len() + " remaining=" + this._abandonedPairs.len());
  }
}

/* Liaison aerienne passagers a fort ROI. Deploie la tresorerie excedentaire sans A*. */
function OpexAI::_tryBuildAir(year)
{
  /* La garde testait `airCombos == null && airport == null`. Deux defauts (docs/taches.md
   * S0 sexies) : `_refreshAir` pose TOUJOURS une liste, meme vide (catalog.nut met `[]` avant sa
   * sortie anticipee), donc la garde ne pouvait jamais se declencher sur « aucun avion
   * disponible » et la fonction partait dans sa boucle sur des cartes sans combo ; et le seul etat
   * qu'elle laissait passer -- `airCombos == null` avec `airport != null` -- faisait dereferencer
   * `airCombos.len()` plus bas, ce qui TUE l'IA. On teste desormais la vacuite reelle, et le
   * deref est protege a son propre site. */
  local combos = this._catalog.airCombos;
  if ((combos == null || combos.len() == 0) && this._catalog.airport == null) {
    if (DECISION_LOG) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (_lastAirRefuseMonth != ym) {
        _lastAirRefuseMonth = ym;
        OpexDecide("AIR_REFUSE", "reason=no_aircraft_and_airport");
      }
    }
    return;
  }
  local maxPerYear = 30;
  local maxTotal = 250;
  local maxBatch = 12;
  local builtCount = 0;
  while (builtCount < maxBatch) {
    local airLinesThisYear = 0;
    local totalAirLines = 0;
    foreach (line in this._lines) {
      if (("mode" in line) && line.mode == "air") {
        totalAirLines++;
        if (line.year == year) airLinesThisYear++;
      }
    }
    if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=line_cap_reached lines_year=" + airLinesThisYear + " max_year=" + maxPerYear + " total=" + totalAirLines + " max_total=" + maxTotal);
        }
      }
      break;
    }

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local borrowable = REBORROW ? (AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount()) : 0;
    if (borrowable < 0) borrowable = 0;
    local baseReserve = OpexCashReserve();
    /* ⚠️ NE PAS « CORRIGER » CE 2 000 EN LE PORTANT A LA MARGE MAXIMALE. Essaye et MESURE le
     * 2026-09-02 (results/bench_lotE_air_marge_3y.json) : -11,5 % de valeur (t = -2,66), -9,8 % de
     * note officielle (t = -3,25), -11,2 % de gares.
     *
     * Le defaut apparent est reel : le test d'acceptation plus bas exige `requiredMargin` (jusqu'a
     * 30 000 pour deux aeroports neufs), donc un plan tombant dans cette bande est trouve puis
     * rejete, et le `break` gache le cycle. Mais `maxCapital` n'est PAS qu'un filtre : c'est le
     * budget avec lequel OpexAirPlans CHOISIT le plan a proposer. Le reduire de 30 000 partout
     * appauvrit la selection dans tous les cas ou l'ancienne marge suffisait -- notamment le
     * hub-a-hub, dont la marge reelle n'est que 2 000. On echange une boucle bloquee rare contre
     * une degradation systematique.
     *
     * La bonne correction passerait par le plan, pas par le budget : soit passer la marge exigee a
     * OpexAirPlans pour qu'il l'applique par plan, soit ne pas `break` sur rejet et reessayer avec
     * un budget rabote. Voir docs/taches.md. */
    local maxCapital = money + borrowable - baseReserve - 2000;
    if (maxCapital <= 0) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=insufficient_capital cash=" + money + " reserve=" + baseReserve);
        }
      }
      break;
    }

    this._budget.begin();
    local plan = OpexAirPlans(this._catalog, this._lines, maxCapital, null,
                              (AIR_ABANDON && ABANDON_MEMORY) ? this._abandonedPairs : null);
    local planOps = this._budget.end("build_air_plans");
    if (plan == null) {
      local nCombos = (this._catalog.airCombos == null) ? -1 : this._catalog.airCombos.len();
      if (builtCount == 0) {
        /* airCombos peut etre null : ne jamais dereferencer pour un panneau de diagnostic. */
        OpexSign(AIMap.GetTileIndex(1, 1), "AD|NULL|C=" + nCombos);
      }
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=no_candidate combos=" + nCombos);
        }
      }
      break;
    }

    local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
    local requiredMargin = AIR_MARGIN_V2
          ? ((newAirports == 2) ? 15000 : (newAirports == 1 ? 6000 : 0))
          : ((newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000));
    local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
    local need = capital + baseReserve + requiredMargin;
    if (money < need) {
      if (REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (_lastAirRefuseMonth != ym) {
            _lastAirRefuseMonth = ym;
            OpexDecide("AIR_REFUSE", "reason=insufficient_cash cash=" + money + " need=" + need + " capital=" + capital + " margin=" + requiredMargin);
          }
        }
        break;
      }
    }

    local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
    local anchor = AIMap.GetTileIndex(1, 1);
    OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
    if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
    if (AIR_COST_PROBE) {
      OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                             + result.actualCost + "|"
                             + (("planes" in plan) ? plan.planes : 1) + "|"
                             + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (DECISION_LOG) {
        OpexDecide("AIR_REFUSE", "reason=build_failed detail=" + result.reason + " error=" + result.error + " dist=" + plan.distance + " cost=" + result.actualCost);
      }
      /* air_abandon : sans cette memorisation, le cycle suivant re-scanne tous les sites pour
       * reproposer EXACTEMENT le meme bestPlan et echouer de la meme facon. Le chemin
       * portefeuille memorise deja ses echecs (voir plus bas) ; ce chemin-ci ne le faisait pas. */
      if (AIR_ABANDON && ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) {
        this._markPairAbandoned("air|" + plan.siteA.town.tile + "|" + plan.siteB.town.tile);
      }
      break;
    }

    this._airBuilt = true;
    if (DECISION_LOG) {
      OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital + " planes=" + result.vehicles.len());
    }
    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
      cargo = this._catalog.paxCargo,
      predicted = ("economics" in plan && "profitAnnual" in plan.economics) ? plan.economics.profitAnnual : 0,
      predRevenue = plan.economics.revenueAnnual, predRunning = plan.economics.runningAnnual,
      predAmort = plan.economics.amortAnnual, predCarried = plan.economics.carried,
      predTrains = plan.planes, predOneWayDays = plan.economics.oneWayDays,
      planeCapacity = plan.plane.capacity,
      sharedAirportA = ("reuseA" in plan) && plan.reuseA,
      hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
      joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
      joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
      actualCapital = plan.capital,
      iterations = 0, trains = result.vehicles.len(), distance = plan.distance, year = year,
      buildDate = AIDate.GetCurrentDate(),
      mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
      vehCount = result.vehicles.len(),
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
      isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
      lineId = this._nextLineId,
    });
    OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                           + plan.economics.profitAnnual);
    OpexSign(anchor, "AH|" + this._nextLineId + "|"
                     + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                     + plan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
    OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                     + AICargo.GetCargoLabel(this._catalog.paxCargo));
    this._nextLineId++;
    builtCount++;
  }
}

/* Une seule route v1 ; le scan apres rechargement empeche tout doublon maritime. */
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
/* Compte le nombre de stations actives de notre compagnie dans une ville donnee. */
function OpexCountTownStations(townId)
{
  local stations = AIStationList(AIStation.STATION_ANY);
  stations.Valuate(AIStation.GetNearestTown);
  stations.KeepValue(townId);
  return stations.Count();
}

/* Liste des villes desservies par au moins une liaison rail, air ou route de notre compagnie. */
function OpexGetServedTowns(lines)
{
  local townMap = {};
  local result = [];
  foreach (line in lines) {
    local stA = AIStation.GetStationID(line.stationA);
    local stB = AIStation.GetStationID(line.stationB);
    if (AIStation.IsValidStation(stA)) {
      local tA = AIStation.GetNearestTown(stA);
      if (tA >= 0 && !(tA in townMap)) {
        townMap.rawset(tA, true);
        result.append(tA);
      }
    }
    if (AIStation.IsValidStation(stB)) {
      local tB = AIStation.GetNearestTown(stB);
      if (tB >= 0 && !(tB in townMap)) {
        townMap.rawset(tB, true);
        result.append(tB);
      }
    }
  }
  return result;
}

/* Tache basse priorite de croissance urbaine : si une ville desservie compte n gares/aeroports (n < 5),
 * construit 5 - n stations de bus pour porter le total a 5 (plafond de croissance maximale OpenTTD). */
function OpexAI::_tryTownGrowth(year)
{
  if (!TOWN_GROWTH_ENABLED || this._catalog.roadType < 0 || this._catalog.paxCargo < 0) return;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < OpexCashReserve() + 25000) return;

  local engine = (this._catalog.paxCargo in this._catalog.roadEngineByCargo)
      ? this._catalog.roadEngineByCargo[this._catalog.paxCargo] : null;
  if (engine == null) return;

  local servedTowns = OpexGetServedTowns(this._lines);
  if (servedTowns.len() == 0) return;

  local anchor = AIMap.GetTileIndex(1, 1);

  foreach (townId in servedTowns) {
    if (!AITown.IsValidTown(townId)) continue;
    local currentCount = OpexCountTownStations(townId);
    if (currentCount >= 5) continue;

    local townTile = AITown.GetLocation(townId);
    local townPop = AITown.GetPopulation(townId);
    if (townPop < 100) continue;

    local cx = AIMap.GetTileX(townTile);
    local cy = AIMap.GetTileY(townTile);
    local srcCenter = townTile;
    local offsets = [[6, 0], [-6, 0], [0, 6], [0, -6], [6, 6], [-6, -6], [8, 0], [0, 8]];
    local dstCenter = null;
    foreach (off in offsets) {
      local tx = cx + off[0];
      local ty = cy + off[1];
      if (OpexRoadInMap(tx, ty)) {
        local t = AIMap.GetTileIndex(tx, ty);
        if (AITile.GetClosestTown(t) == townId && AITile.GetCargoProduction(t, this._catalog.paxCargo, 1, 1, 3) > 0) {
          dstCenter = t;
          break;
        }
      }
    }
    if (dstCenter == null) {
      dstCenter = townTile + AIMap.GetTileIndex(5, 5);
      if (!AIMap.IsValidTile(dstCenter) || AITile.GetClosestTown(dstCenter) != townId) dstCenter = townTile;
    }

    local dist = AIMap.DistanceManhattan(srcCenter, dstCenter);
    if (dist < 4) dist = 5;

    local candidate = {
      src = srcCenter,
      dst = dstCenter,
      srcTown = townId,
      dstTown = townId,
      cargo = this._catalog.paxCargo,
      kind = "pax",
      distance = dist,
      trains = 1,
      engine = engine,
      capital = 2 * this._catalog.costRoadBusStop + 20 * this._catalog.costRoadPerTile + this._catalog.costRoadDepot + engine.price,
      revenueAnnual = 0,
      runningAnnual = 0,
      amortAnnual = 0,
      carried = 0,
      oneWayDays = 1,
      iterations = 0,
      profitAnnual = 0,
      effectiveSpeed = engine.speed,
    };

    this._budget.begin();
    local planning = OpexRoadPlanFor(this._catalog, candidate);
    local planOps = this._budget.end("build_road_plans");
    local plan = planning.plan;
    if (plan == null) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=plan detail=" + planning.reason);
      }
      continue;
    }

    local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
    if (actualDist < 1) actualDist = 1;
    candidate.distance = actualDist;
    local routeDist = (plan.routeDistance != null && plan.routeDistance > 0) ? plan.routeDistance : actualDist;
    candidate.capital = 2 * this._catalog.costRoadBusStop + routeDist * this._catalog.costRoadPerTile + this._catalog.costRoadDepot + candidate.engine.price;

    local need = candidate.capital + OpexCashReserve();
    money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=cash need=" + need + " cash=" + money);
      }
      continue;
    }
    /* growth_yields : la croissance urbaine batit des lignes a profitAnnual = 0 et
     * revenueAnnual = 0 EXPLICITES (voir le candidat construit ci-dessus). Son rendement est
     * indirect -- faire grossir la ville pour nourrir les autres lignes -- mais son capital, lui,
     * est bien reel et immediat. Or le goulot mesure de cette IA est la VITESSE DU CAPITAL :
     * 44,5 % de la valeur d'entreprise dort en caisse, et un seul projet est bati par mois
     * (docs/taches.md S0 decies). Cette depense a rendement nul entre donc en concurrence directe
     * avec les projets rentables du portefeuille.
     *
     * Sous 1, la croissance urbaine ne prend que le capital dont le portefeuille NE VEUT PAS :
     * elle exige un surplus au-dela de ce que celui-ci s'est deja engage a depenser
     * (`selectedCapital`). Elle cede donc le pas sans jamais etre supprimee. */
    if (GROWTH_YIELDS && this._projects != null) {
      local committed = ("stats" in this._projects) ? this._projects.stats.selectedCapital : 0;
      if (money < need + committed) {
        if (DECISION_LOG) {
          OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                     + " reason=committed need=" + need + " committed=" + committed
                     + " cash=" + money);
        }
        continue;
      }
    }

    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    if (ROAD_COST_PROBE) {
      OpexSign(anchor, "RP|" + townId + "|" + result.plannedCapital + "|" + result.actualCost
                             + "|" + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=build detail=" + result.reason + " error=" + result.error
                   + " dist=" + actualDist);
      }
      continue;
    }

    local newCount = OpexCountTownStations(townId);
    OpexSign(anchor, "TG|" + (year % 100) + "|" + townId + "|" + currentCount + "|" + newCount);
    if (DECISION_LOG) {
      OpexDecide("TOWN_GROWTH", "action=build town=" + townId + " stations_before=" + currentCount + " stations_after=" + newCount + " cost=" + candidate.capital);
    }

    this._lines.append({
      stationA = result.stopA, stationB = result.stopB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = 0, iterations = 0, trains = result.vehicles.len(), distance = dist, year = year,
      predRevenue = 0, predRunning = 0, predAmort = 0, predCarried = 0, predTrains = 1, predOneWayDays = 1,
      /* Batie pour la CROISSANCE de la ville, pas pour son profit : son candidat porte
       * revenueAnnual = 0 EXPLICITE. A exclure nommement d'une comparaison predit/reel, et non
       * devinee par pred_rev == 0 -- 21 a 23 % des enregistrements du diagnostic. */
      purpose = "town_growth",
      effectiveSpeed = engine.speed, catalogSpeed = engine.speed,
      mode = "road", kind = "pax", depot = result.depot,
      nStopsA = result.nStopsA, nStopsB = result.nStopsB,
      srcIndustry = -1, dstIndustry = -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = this._nextLineId,
    });
    this._nextLineId++;
    break;
  }
}

/* Precalcule le trace des meilleurs candidats en avance pendant les ticks d'opcodes dormants. */
/* Une extremite deja desservie par nous ne merite pas un second raccordement.
 *
 * Deux tests distincts, mesure du 2026-08-28 a l'appui (results/opex_full_campaign_20y.json,
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
    /* Seules les lignes ferroviaires comptent pour la separation de bassin et gares ferroviaires. */
    if (("mode" in line) && line.mode != "rail") continue;
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
    if (("mode" in line) && line.mode != "rail") continue;
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

/* Revalidation air du batch : un plan garde ses deux sites depuis la generation, mais un succes
 * precedent a pu y poser une gare, une route ou un aeroport. Ce probe ne tourne donc JAMAIS pour
 * le premier projet ; le precedent mesure est maxBatch=1, ou le plan etait encore celui de la
 * generation. Il reprend le test utile de OpexAirFindSite, y compris le nivellement que le vrai
 * constructeur fera, sans relancer OpexAirPlans ni ses panneaux. */
function OpexAirBatchSiteStillBuildable(site, airport, plane, reuse)
{
  if (reuse) {
    return AIAirport.IsAirportTile(site.anchor) &&
           OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(site.anchor), plane.planeType);
  }
  local end = site.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
  if (!AIMap.IsValidTile(end)) return false;
  local ok = false;
  {
    local probe = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
    if (!ok) {
      local error = AIError.GetLastError();
      if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
      else {
        AITile.LevelTiles(site.anchor, end);
        ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
        if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
      }
    }
  }
  return ok;
}

/* Un hub garde une limite de routes liee a son aeroport. La generation l'avait controlee sur
 * l'ancien this._lines ; apres un succes de batch, seul ce comptage vivant peut dire si le plan
 * reste admissible. Pas de controle de taille de flotte ici : plan.planes ne depend d'aucun etat
 * modifie par le chantier precedent et le relire serait du cout d'opcodes sans information. */
function OpexAirBatchHubHasCapacity(anchor, plane, lines)
{
  if (!AIAirport.IsAirportTile(anchor) ||
      !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(anchor), plane.planeType)) return false;
  local station = AIStation.GetStationID(anchor);
  if (!AIStation.IsValidStation(station)) return false;
  local routes = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    /* this._lines garde les tuiles d'aeroport, pas les StationID. Comparer les tuiles au
     * StationID du hub laisserait passer le plafond apres le premier succes du batch. */
    if (AIStation.GetStationID(line.stationA) == station ||
        AIStation.GetStationID(line.stationB) == station) routes++;
  }
  local airportType = AIAirport.GetAirportType(anchor);
  local maxRoutes = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  return routes < maxRoutes;
}

/* La paire O/D et les bouts nouveaux etaient valides dans le portefeuille fige. Apres un succes,
 * ils peuvent desormais etre deja servis ; on les ecarte plutot que de laisser le constructeur
 * detruire puis echouer. Les scans sont bornes par PORTFOLIO_MAX_BATCH <= 8 et absents du controle
 * maxBatch=1, pour ne pas recreer le cout de panneaux qui avait deplace les frontieres de ticks. */
function OpexAirBatchPlanStillLive(plan, lines)
{
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA && OpexAirTownServed(plan.siteA.town, lines)) return false;
  if (!reuseB && OpexAirTownServed(plan.siteB.town, lines)) return false;
  if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == plan.siteA.town.tile && line.originB == plan.siteB.town.tile) ||
        (line.originA == plan.siteB.town.tile && line.originB == plan.siteA.town.tile)) return false;
  }
  return true;
}

/* Les docks sont des sites figes, contrairement au trace routier qui est recalcule juste avant
 * OpexBuildRoadRoute. La connexion eau elle-meme n'est pas re-scannee : aucun premier chantier
 * non maritime ne peut modifier ses aretes, et un premier chantier maritime met _waterBuilt a 1.
 * Ce probe couvre donc le seul etat que le batch peut invalider sans payer un BFS inutile. */
function OpexWaterBatchSiteStillBuildable(site)
{
  local ok = false;
  { local probe = AITestMode(); ok = AIMarine.BuildDock(site.dock, AIStation.STATION_NEW); }
  return ok;
}

/* Le coeur de l'allocation : on descend le classement tant qu'il reste de l'argent, et chaque
 * tentative recoit un budget d'iterations egal a ce qu'il faut pour continuer a battre le
 * candidat SUIVANT. Pour le dernier, l'alternative reelle n'est pas l'absence de travail : c'est
 * attendre le prochain rafraichissement annuel et son classement. MIN_RATIO est precisement le
 * plus petit rapport acceptable dans ce classement ; il remplace donc le suivant absent, sans
 * introduire de seuil propre a l'arret. */
/* Construction multimodale du portefeuille ROI. Parcourt les projets finances ordonnes par opcodeScore,
 * emet le panneau de decision IP et dispatch vers le constructeur specialise. En cas de succes, le portefeuille
 * est immediatement regenere car le capital et les origines ont change. */
function OpexFeederCandidateCompare(a, b)
{
  /* C29.4 : Priorité absolue à la première desserte de chaque ville (slot 0)
   * sur les extensions secondaires multi-arrêts (slot >= 1) */
  local slotA = ("feederSlot" in a) ? a.feederSlot : 0;
  local slotB = ("feederSlot" in b) ? b.feederSlot : 0;
  if (slotA != slotB) {
    if (slotA < slotB) return -1;
    return 1;
  }
  if (a.roi > b.roi) return -1;
  if (a.roi < b.roi) return 1;
  local aProf = a.profitAnnual + (("networkProfit" in a) ? a.networkProfit : 0);
  local bProf = b.profitAnnual + (("networkProfit" in b) ? b.networkProfit : 0);
  if (aProf > bProf) return -1;
  if (aProf < bProf) return 1;
  return 0;
}

/* Tâche dédiée de rabattage bus (feeders) vers les hubs aéroportuaires et ferroviaires (docs/taches.md C1).
 * Décloisonnée du sac à dos principal pour ne pas être écrasée par l'opcodeScore des lignes aériennes. */
function OpexAI::_tryBuildFeeders(year)
{
  if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) return false;
  if (this._lines.len() == 0) return false;

  local candidates = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
    economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
    feederHubs = 0, feederCandidates = 0,
    roadDistanceShort = 0, roadDistanceLong = 0,
  };
  /* C31.2 : la generation de feeders etait comptabilisee tant qu'elle vivait dans
   * OpexBuildRoadCandidates (budget "cand_road"). C29.3 l'en a sortie -- a juste titre, pour
   * supprimer la collision d'OD -- mais l'appelait NUE, alors que la fonction avait triple de
   * taille. Sur un projet ou l'opcode est une ressource, la seule fonction qui grossit ne peut pas
   * etre celle qu'on cesse de mesurer. */
  this._budget.begin();
  OpexRoadFeederCandidates(this._catalog, this._lines, candidates, stats);
  local feederGenOps = this._budget.end("cand_feeders");
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  AILog.Info("FD|" + yy + "|" + stats.feederHubs + "|" + stats.feederCandidates + "|" + candidates.len());
  OpexSign(anchor, "FD|" + yy + "|" + stats.feederHubs + "|" + stats.feederCandidates + "|" + candidates.len());
  if (DECISION_LOG) {
    OpexDecide("FEEDER_GEN", "hubs=" + stats.feederHubs + " towns_scanned=" + this._catalog.towns.len()
               + " candidates=" + stats.feederCandidates + " opcodes=" + feederGenOps);
  }
  if (candidates.len() == 0) {
    if (DECISION_LOG && stats.feederHubs > 0) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (_lastFeederRefuseMonth != ym) {
        _lastFeederRefuseMonth = ym;
        OpexDecide("FEEDER_REFUSE", "reason=no_candidates hubs=" + stats.feederHubs + " pairs_in_band=" + stats.pairsInBand + " no_monthly=" + stats.noMonthly + " profit_too_low=" + stats.profitTooLow);
      }
    }
    return false;
  }

  candidates.sort(OpexFeederCandidateCompare);

  /* rabattage_diag (2026-09-02) : n_feeders reste a 0 sur les 5 graines du banc alors que
   * feederCandidates > 0 chaque annee -- ce compteur dit a QUELLE garde de cette boucle les
   * candidats meurent. Ajoute pour diagnostic, pas pour changer le comportement. */
  local rejectStats = {
    served = 0, townCount = 0, abandoned = 0, cash = 0, planNull = 0, buildFail = 0,
    hubNew = 0, hubSaturated = 0,
  };

  foreach (candidate in candidates) {
    local isHubTown = ("isHubTown" in candidate) ? candidate.isHubTown : false;
    if (FEEDER_UNLOCK) {
      local maxFeeders = 1;
      if (isHubTown && FEEDER_TOWN_COVERAGE) {
        local tId = ("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(candidate.src);
        local houses = AITown.IsValidTown(tId) ? AITown.GetHouseCount(tId) : 0;
        if (houses <= 0 && AITown.IsValidTown(tId)) houses = AITown.GetPopulation(tId) / 25;
        maxFeeders = OpexCeilDiv(houses, ROAD_STOP_CATCHMENT_HOUSES);
        if (maxFeeders > 4) maxFeeders = 4;
        if (maxFeeders < 1) maxFeeders = 1;
      }
      if (OpexTownFeederCount(this._lines, candidate.src, candidate.hubStationId) >= maxFeeders) { rejectStats.served++; continue; }
    } else {
      if (OpexRoadPairServed(this._lines, candidate.src, candidate.dst)) { rejectStats.served++; continue; }
    }
    if (!isHubTown && OpexTownRoadLineCount(this._lines, candidate.src) >= 4) { rejectStats.townCount++; continue; }

    local abandonedKey = OpexAbandonedPairKey(candidate);
    if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) { rejectStats.abandoned++; continue; }

    local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
    local yearsElapsed = (this._startYear >= 0) ? (year - this._startYear) : 0;
    if (slot >= 1 && yearsElapsed < 2) { rejectStats.served++; continue; }

    if (FEEDER_HUB_CHECK && ("hubStationId" in candidate) && AIStation.IsValidStation(candidate.hubStationId)) {
      /* Trouver la ligne reliant ce hub, son age et sa capacite */
      local hubAgeDays = -1;
      local hubCapacity = 25;
      foreach (line in this._lines) {
        if (("stationA" in line) && ("stationB" in line)) {
          local stA = OpexLineStationId(line, "A");
          local stB = OpexLineStationId(line, "B");
          if (stA == candidate.hubStationId || stB == candidate.hubStationId) {
            if ("buildDate" in line) {
              local age = AIDate.GetCurrentDate() - line.buildDate;
              if (hubAgeDays < 0 || age < hubAgeDays) hubAgeDays = age;
            }
            if (("capacity" in line) && line.capacity > hubCapacity) {
              hubCapacity = line.capacity;
            }
          }
        }
      }

      local hubPaxRating = AIStation.GetCargoRating(candidate.hubStationId, this._catalog.paxCargo);
      local hubPaxWait = AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.paxCargo);

      /* 1. Hub immature : ligne trop jeune (< FEEDER_HUB_MIN_DAYS) ou aucune rotation achevee (rating < 0) */
      if ((hubAgeDays >= 0 && hubAgeDays < FEEDER_HUB_MIN_DAYS) || hubPaxRating < 0) {
        if (DECISION_LOG) {
          OpexDecide("FEEDER_REJECT", "reason=hub_immature hub=" + candidate.hubStationId + " age=" + hubAgeDays + " min_days=" + FEEDER_HUB_MIN_DAYS + " rating=" + hubPaxRating);
        }
        rejectStats.hubNew++;
        continue;
      }

      /* 2. Hub deja pourvu de passagers : le stock en attente depasse la capacite ou le seuil.
       * Inutile d'investir le cash de demarrage dans un feeder quand le tarmac a deja assez de clients. */
      local maxWait = (FEEDER_HUB_WAIT_MAX > 0) ? FEEDER_HUB_WAIT_MAX : (hubCapacity * 2);
      if (hubPaxWait >= maxWait) {
        if (DECISION_LOG) {
          OpexDecide("FEEDER_REJECT", "reason=hub_saturated hub=" + candidate.hubStationId + " wait=" + hubPaxWait + " max=" + maxWait);
        }
        rejectStats.hubSaturated++;
        continue;
      }
    }

    local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (slot >= 1) {
      /* C29.4 : Un arrêt secondaire ne s'endette jamais pour se construire :
       * il exige que l'entreprise dispose du cash disponible. */
      if (money < need) { rejectStats.cash++; continue; }
    } else {
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) { rejectStats.cash++; continue; }
    }

    this._budget.begin();
    local planning = OpexRoadPlanFor(this._catalog, candidate);
    local planOps = this._budget.end("build_road_plans");
    local plan = planning.plan;
    local idx = this._nextLineId;
    if (plan == null) {
      if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
      AILog.Info("PLAN_FAIL: cand=" + candidate.src + "->" + candidate.dst + " slot=" + slot + " reason=" + planning.reason);
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
      rejectStats.planNull++;
      continue;
    }
    local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
    if (actualDist < 1) actualDist = 1;
    local economics = OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,
                                            candidate.monthly, candidate.engine, candidate.kind,
                                            plan.routeDistance);
    if (economics != null) {
      local netProfit = ("networkProfit" in candidate) ? candidate.networkProfit : 0;
      local netRev = ("networkRevenue" in candidate) ? candidate.networkRevenue : 0;
      OpexApplyRoadEconomics(candidate, economics, actualDist);
      if (netProfit > 0) {
        candidate.profitAnnual += netProfit;
        candidate.revenueAnnual += netRev;
        if (candidate.capital > 0) {
          candidate.roi = (candidate.profitAnnual * 1000) / candidate.capital;
        }
      }
    }
    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    if (ROAD_COST_PROBE) {
      OpexSign(anchor, "RP|" + idx + "|" + result.plannedCapital + "|" + result.actualCost
                             + "|" + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
      rejectStats.buildFail++;
      continue;
    }

    this._lines.append({
      stationA = result.stopA, stationB = result.stopB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = candidate.profitAnnual,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      iterations = candidate.iterations, trains = candidate.trains, distance = candidate.distance,
      year = year, mode = "road",
      vehicles = result.vehicles,
      depot = result.depot,
      capacity = result.capacity,
      nStopsA = result.nStopsA,
      nStopsB = result.nStopsB,
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = this._nextLineId,
      isFeeder = true,
      /* Un feeder DECHARGE dans un hub : son revenu propre n'est pas sa raison d'etre, et le
       * comparer a une liaison interurbaine n'a pas de sens. Motif explicite pour que le
       * diagnostic predit/reel le separe au lieu de le noyer dans la route pax. */
      purpose = "feeder",
      hubStationId = candidate.hubStationId,
      srcTown = candidate.srcTown,
      feederSlot = ("feederSlot" in candidate) ? candidate.feederSlot : 0,
    });
    if (DECISION_LOG) {
      local hubMode = ("hubMode" in candidate) ? candidate.hubMode : "unknown";
      local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
      local hubPaxWait = AIStation.IsValidStation(candidate.hubStationId) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.paxCargo) : -1;
      local hubPaxRating = AIStation.IsValidStation(candidate.hubStationId) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.paxCargo) : -1;
      local hubMailWait = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.mailCargo) : -1;
      local hubMailRating = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.mailCargo) : -1;
      OpexDecide("FEEDER_BUILD", "line=" + this._nextLineId + " hub=" + candidate.hubStationId + " hub_mode=" + hubMode + " src=" + candidate.src + " dst=" + candidate.dst + " slot=" + slot + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + candidate.capital + " hub_pax_wait=" + hubPaxWait + " hub_pax_rating=" + hubPaxRating + " hub_mail_wait=" + hubMailWait + " hub_mail_rating=" + hubMailRating);
    }
    AILog.Info("FE|" + yy + "|" + this._nextLineId + "|" + candidate.distance + "|" + candidate.profitAnnual);
    OpexSign(anchor, "FE|" + yy + "|" + this._nextLineId + "|" + candidate.distance + "|" + candidate.profitAnnual);
    this._nextLineId++;

    /* C29.5 : Duplication automatique des bus de rabattement par des camions postaux (modele AAAHogEx #M1) */
    if (FEEDER_MAIL_DUPLICATE) {
      this._tryBuildMailFeeder(candidate, result, year);
    }

    return true;
  }
  if (DECISION_LOG) {
    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    if (_lastFeederRefuseMonth != ym) {
      _lastFeederRefuseMonth = ym;
      OpexDecide("FEEDER_REFUSE", "reason=all_rejected hubs=" + stats.feederHubs + " candidates=" + stats.feederCandidates + " served=" + rejectStats.served + " town_limit=" + rejectStats.townCount + " abandoned=" + rejectStats.abandoned + " cash=" + rejectStats.cash + " hub_immature=" + rejectStats.hubNew + " hub_saturated=" + rejectStats.hubSaturated + " no_plan=" + rejectStats.planNull + " build_fail=" + rejectStats.buildFail);
    }
  }
  OpexSign(anchor, "FZ|" + yy + "|" + rejectStats.served + "|" + rejectStats.townCount + "|"
                         + rejectStats.abandoned + "|" + rejectStats.cash + "|"
                         + rejectStats.planNull + "|" + rejectStats.buildFail);
  return false;
}

/* G11 : le placement d'un arret camion peut ajouter une ou deux aretes. Les supprimer a partir
 * de la liste exacte, en ordre inverse, evite de laisser une branche orpheline tout en ne touchant
 * jamais la voirie qui precedait la tentative. */
function OpexMailRollbackStop(stop)
{
  if (stop == null || !stop.isNew) return;
  if (AIRoad.IsRoadStationTile(stop.tile)) AIRoad.RemoveRoadStation(stop.tile);
  if ("added" in stop) {
    for (local i = stop.added.len() - 1; i >= 0; i--) {
      AIRoad.RemoveRoad(stop.added[i].from, stop.added[i].to);
    }
  }
}

function OpexMailRollbackStops(stopA, stopB)
{
  OpexMailRollbackStop(stopB);
  OpexMailRollbackStop(stopA);
}

function OpexAI::_tryBuildMailFeeder(candidate, paxResult, year)
{
  if (!FEEDER_MAIL_DUPLICATE) return false;
  if (this._catalog.mailCargo < 0) return false;
  if (!(this._catalog.mailCargo in this._catalog.roadEngineByCargo)) return false;
  if (paxResult == null || paxResult.stopA == null || paxResult.stopB == null || paxResult.depot == null) return false;

  local mailCargo = this._catalog.mailCargo;
  local mailEngine = this._catalog.roadEngineByCargo[mailCargo];
  local costEstimate = mailEngine.price + 2000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < costEstimate + OpexCashReserve()) {
    if (REBORROW) money = OpexTryReborrow(costEstimate + OpexCashReserve(), money);
    if (money < costEstimate + OpexCashReserve()) return false;
  }

  local stopA = paxResult.stopA;
  local stopB = paxResult.stopB;
  local frontA = AIRoad.GetRoadStationFrontTile(stopA);
  local frontB = AIRoad.GetRoadStationFrontTile(stopB);
  local stationA = AIStation.GetStationID(stopA);
  local stationB = AIStation.GetStationID(stopB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) return false;

  // 1. Trouver ou construire l'arret camion cote ville (A)
  local mailStopA = OpexRoadFindOrBuildTruckStop(this._catalog, stopA, frontA, stationA);
  if (mailStopA == null) return false;

  // 2. Trouver ou construire l'arret camion cote hub (B)
  local mailStopB = OpexRoadFindOrBuildTruckStop(this._catalog, stopB, frontB, stationB);
  if (mailStopB == null) {
    OpexMailRollbackStops(mailStopA, null);
    return false;
  }

  // 3. Verifier la capacite refit
  local capacity = OpexRoadRefitCapacity(paxResult.depot, mailEngine, mailCargo);
  if (capacity <= 0) {
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 4. Construire le camion postal dans le depot partage
  local truck = AIVehicle.BuildVehicleWithRefit(paxResult.depot, mailEngine.id, mailCargo);
  if (!AIVehicle.IsValidVehicle(truck)) {
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 5. Ordres : ramassage ville (OF_NONE) -> dechargement transfert hub (OF_TRANSFER)
  local orderA = AIOrder.AppendOrder(truck, mailStopA.tile, AIOrder.OF_NONE);
  local orderB = AIOrder.AppendOrder(truck, mailStopB.tile, AIOrder.OF_TRANSFER);
  if (!orderA || !orderB || AIOrder.GetOrderCount(truck) != 2) {
    AIVehicle.SellVehicle(truck);
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 6. Demarrer le camion postal
  if (!AIVehicle.StartStopVehicle(truck)) {
    AIVehicle.SellVehicle(truck);
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 7. Enregistrer la ligne postale
  local yy = year % 100;
  local anchor = AIMap.GetTileIndex(1, 1);
  this._lines.append({
    stationA = mailStopA.tile, stationB = mailStopB.tile,
    originA = candidate.src, originB = candidate.dst,
    cargo = mailCargo,
    predicted = candidate.profitAnnual / 4,
    predRevenue = candidate.revenueAnnual / 4, predRunning = mailEngine.runningCost * 2,
    predAmort = 0, predCarried = candidate.carried / 4,
    predTrains = 1, predOneWayDays = candidate.oneWayDays,
    iterations = 1, trains = 1, distance = candidate.distance,
    year = year, mode = "road",
    vehicles = [truck],
    depot = paxResult.depot,
    capacity = capacity,
    nStopsA = 1, nStopsB = 1,
    isLowRatio = false,
    opcodeRatio = -1,
    lineId = this._nextLineId,
    isFeeder = true,
    purpose = "feeder_mail",
    hubStationId = candidate.hubStationId,
    srcTown = candidate.srcTown,
    feederSlot = ("feederSlot" in candidate) ? candidate.feederSlot : 0,
  });
  if (DECISION_LOG) {
    local hubMailWait = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.mailCargo) : -1;
    local hubMailRating = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.mailCargo) : -1;
    OpexDecide("FEEDER_MAIL_BUILD", "line=" + this._nextLineId + " hub=" + candidate.hubStationId
               + " src=" + candidate.src + " dst=" + candidate.dst + " truck=" + truck
               + " hub_mail_wait=" + hubMailWait + " hub_mail_rating=" + hubMailRating);
  }
  AILog.Info("FM|" + yy + "|" + this._nextLineId + "|" + candidate.distance);
  OpexSign(anchor, "FM|" + yy + "|" + this._nextLineId + "|" + candidate.distance);
  this._nextLineId++;
  return true;
}

/* C38 etape 2 : une tentative rail est une transaction explicite. Le balayage decide
 * seulement quoi faire ensuite ; cette fonction decide si le candidat a ete construit,
 * refuse, ou suspendu par A*. `passDiscards` reste une reference partagee pour
 * conserver le journal dans le meme ordre que le passage historique. */
function OpexAI::_tryBuildRailProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local candidate = project.payload;
      if (builtCount > 0 && ("railPlan" in candidate)) {
        /* Le trace A* memorise vise la carte de la generation. Le premier chantier peut avoir
         * occupe un quai, un depot ou une tuile du trace ; le jeter force OpexBuildLine a
         * replanifier sur la carte vivante. Inerte pour maxBatch=1, precedent mesure. */
        candidate.railPlan = null;
      }
      /* Une recherche est deja en cours (autre candidat, ou upgrade) : ne pas en lancer une
       * seconde, et laisser air/route du portefeuille tourner. */
      if (RAIL_SEARCH_RESUMABLE && this._railSearch != null) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "search_in_progress", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local close = this._tooClose(candidate);
      local join = null;
      local placeJoin = ("placeJoin" in candidate) ? candidate.placeJoin : null;
      if (close.hard >= 0) {
        if (DECISION_LOG || C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_hard", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      if (placeJoin != null) {
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
          join = null;
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "place_join_refuse", extra = "refuse=" + refuse });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else if (close.blocking >= 0) {
        if (STATION_JOIN) {
          join = OpexFindStationJoin(candidate, close.conflicts);
          if ("refuse" in join) {
            join = null;
          } else if (JOIN_MAX_DISTANCE > 0 && candidate.distance >= JOIN_MAX_DISTANCE) {
            join = null;
          }
        }
        if (join == null) {
          if (DECISION_LOG || C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }

      local need = candidate.capital + OpexCashReserve();
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      local lowCash = (money < need);
      /* G3§2 : pour le chemin reprenable sans railPlan, la recherche A* ne coute aucune
       * tresorerie et le cash peut arriver pendant les tranches. On ne saute que le chemin
       * non reprenable (construction immediate). _consumeRailSearch verifiera la caisse a
       * la fin. Cela active aussi la branche isPreplanOrLowCash de OpexDynamicHardCap, qui
       * remonte au plafond dur pour exploiter les opcodes dormants pendant l'attente. */
      local willStartSearch = RAIL_SEARCH_RESUMABLE
          && !(("railPlan" in candidate) && candidate.railPlan != null);
      if (lowCash && !willStartSearch) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|T|" + project.budgetScore + "|" + project.opcodeScore);

      local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
      local alternativeRatio = isPaxNear ? 0 : MIN_RATIO;
      local hardCap = OpexDynamicHardCap(this._lines.len(), lowCash);
      /* P1.3 : le devis P1.1 porte le chemin complet. Le reutiliser seulement
       * apres une revalidation AITestMode sur la carte vivante ; un join decide
       * au chantier n'etait pas dans le devis et force donc une replannification. */
      if (RAIL_PREQUOTE_KEEP_PLAN && ("quotedPlan" in candidate) && candidate.quotedPlan != null) {
        if (join == null && OpexRailQuotedPlanStillBuildable(candidate.quotedPlan, join)) {
          candidate.railPlan <- candidate.quotedPlan;
          candidate.quotedPlan = null;
          if (DECISION_LOG) OpexDecide("P1_3_PLAN", "action=reuse src=" + candidate.src
                                       + " dst=" + candidate.dst);
        } else {
          candidate.quotedPlan = null;
          candidate.capitalIsActual = false;
          if (DECISION_LOG) OpexDecide("P1_3_PLAN", "action=invalidate src=" + candidate.src
                                       + " dst=" + candidate.dst + " reason="
                                       + (join == null ? "map" : "join"));
        }
      }
      local posPacked = i * TOP_K + this._projects.best.len();
      if (RAIL_SEARCH_RESUMABLE &&
          !(("railPlan" in candidate) && candidate.railPlan != null)) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
        }
        local start = this._startRailSearch(candidate, join, placeJoin, alternativeRatio,
                                            hardCap, posPacked);
        if (start.pending) return { outcome = "pending", discards = passDiscards };
        /* Le candidat n'a pas encore cette cle dans le chemin qui termine sa
         * recherche dans le meme tour : creation de slot Squirrel avec `<-`. */
        candidate.railPlan <- start.plan;
      }
      local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio, join,
                                   OpexCashReserve(), hardCap);
      if (result.reason == "CASH") {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "cash_at_build", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      if (("railPlan" in candidate)) candidate.railPlan = null;
      if (DECISION_LOG && !RAIL_SEARCH_RESUMABLE) {
        foreach (d in passDiscards) {
          OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
        }
        passDiscards = [];
        local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
        OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=rail kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
      }
      local recorded = this._recordRailAttempt(candidate, result, join, placeJoin, posPacked, year);
      return { outcome = recorded ? "built" : "rejected", discards = passDiscards };

}

/* C38 etape 2 : tentative synchrone eau, au meme contrat que le rail. */
function OpexAI::_tryBuildWaterProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "water", src = project.src, dst = project.dst, reason = "water_unavailable", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local plan = project.payload;
      if (builtCount > 0 && (!OpexWaterBatchSiteStillBuildable(plan.siteA) ||
                             !OpexWaterBatchSiteStillBuildable(plan.siteB))) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "batch_site_unbuildable", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local capital = 2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice;
      local need = capital + OpexCashReserve() + WATER_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|W|" + project.budgetScore + "|" + project.opcodeScore);
      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      local result = OpexBuildWaterRoute(this._catalog, this._budget, plan);
      if (result.ok) OpexSign(anchor, "OM|W|" + year + "|" + plan.distance + "|" + planOps);
      else OpexSign(anchor, "ON|W|" + result.reason + "|" + result.error);
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "build_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=water src=" + plan.siteA.town.id + " dst=" + plan.siteB.town.id + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        return { outcome = "rejected", discards = passDiscards };
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=water cargo=" + cargoStr + " src=" + result.dockA + " dst=" + result.dockB + " dist=" + plan.distance + " cost=" + capital + " roi=" + project.roi);
          OpexDecide("WATER_BUILD", "line=" + this._nextLineId + " src=" + result.dockA + " dst=" + result.dockB + " cargo=" + cargoStr + " dist=" + plan.distance + " cost=" + capital);
        }
        this._waterBuilt = true;
        this._lines.append({
          stationA = result.dockA, stationB = result.dockB,
          originA = result.dockA, originB = result.dockB,
          cargo = this._catalog.paxCargo,
          predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
          mode = "water", vehicle = result.vehicle, vehicles = [result.vehicle],
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        OpexSign(anchor, "PM|" + this._nextLineId + "|W|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        this._nextLineId++;
        return { outcome = "built", discards = passDiscards };
      }
  return { outcome = "rejected", discards = passDiscards };
}

/* C38 etape 2 : une croissance de flotte est une tentative synchrone de portefeuille. */
function OpexAI::_tryBuildFleetProject(year, project, rank, passDiscards)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
  /* C34.2 : les gardes de refus ont deja ete franchies en mode a blanc ; il ne reste que le
   * test de tresorerie du portefeuille, sans droit de tirage anticipe. */
  local entry = project.payload;
  local line = entry.line;
  local need = entry.planePrice + OpexCashReserve();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need && REBORROW) money = OpexTryReborrow(need, money);
  if (money < need) {
    if (DECISION_LOG) passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst, reason = "insufficient_cash", extra = "" });
    return { outcome = "rejected", discards = passDiscards };
  }
  local added = 0;
  for (local k = 0; k < entry.want; k++) {
    local grown = OpexAirAddPlane(line);
    if (grown.added <= 0) break;
    added += grown.added;
    local haveNow = (("vehCount" in line) ? line.vehCount : 0) + grown.added;
    line.vehCount <- haveNow;
    line.trains = haveNow;
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < need) break;
  }
  if (added <= 0) return { outcome = "rejected", discards = passDiscards };

  line.lastAirFleetYear <- year;
  line.lastAirFleetDate <- AIDate.GetCurrentDate();
  if (DECISION_LOG) {
    OpexDecide("FLEET_PROJECT", "action=grow line=" + line.lineId + " added=" + added
               + " want=" + entry.want + " price=" + entry.planePrice
               + " profit=" + project.profitAnnual + " roi=" + project.roi);
  }
  AILog.Info("[FLEET_PROJECT] line=" + line.lineId + " added=" + added);
  return { outcome = "built", discards = passDiscards };
}


/* C38 etape 2 : tentative synchrone air, incluant les gardes de site et de flotte. */
function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local plan = project.payload;
      if (builtCount > 0) {
        if (!OpexAirBatchPlanStillLive(plan, this._lines)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "batch_plan_dead", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                             ("reuseA" in plan) && plan.reuseA)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteA_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                             ("reuseB" in plan) && plan.reuseB)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteB_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local maxPerYear = 30;
      local maxTotal = 250;
      local airLinesThisYear = 0;
      local totalAirLines = 0;
      foreach (line in this._lines) {
        if (("mode" in line) && line.mode == "air") {
          totalAirLines++;
          if (line.year == year) airLinesThisYear++;
        }
      }
      if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "line_cap_reached", extra = "lines_year=" + airLinesThisYear + " total=" + totalAirLines });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = "air|" + plan.siteA.town.tile + "|" + plan.siteB.town.tile;
      if (ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      local requiredMargin = AIR_MARGIN_V2
          ? ((newAirports == 2) ? 15000 : (newAirports == 1 ? 6000 : 0))
          : ((newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000));
      local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
      local need = capital + OpexCashReserve() + requiredMargin;
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|A|" + project.budgetScore + "|" + project.opcodeScore);

      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
      OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
      if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
      if (AIR_COST_PROBE) {
        OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                               + result.actualCost + "|"
                               + (("planes" in plan) ? plan.planes : 1) + "|"
                               + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "build_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=air src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
        return { outcome = "rejected", discards = passDiscards };
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=air cargo=" + cargoStr + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " dist=" + plan.distance + " cost=" + plan.capital + " profit=" + plan.economics.profitAnnual + " roi=" + project.roi);
          OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital + " planes=" + result.vehicles.len());
        }
        this._airBuilt = true;
        this._lines.append({
          stationA = result.stationA, stationB = result.stationB,
          originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
          cargo = this._catalog.paxCargo,
          predicted = ("economics" in plan && "profitAnnual" in plan.economics) ? plan.economics.profitAnnual : 0,
          predRevenue = plan.economics.revenueAnnual, predRunning = plan.economics.runningAnnual,
          predAmort = plan.economics.amortAnnual, predCarried = plan.economics.carried,
          predTrains = plan.planes, predOneWayDays = plan.economics.oneWayDays,
          planeCapacity = plan.plane.capacity,
          sharedAirportA = ("reuseA" in plan) && plan.reuseA,
          hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
          joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
          joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
          actualCapital = plan.capital,
          iterations = 0, trains = result.vehicles.len(), distance = plan.distance, year = year,
          buildDate = AIDate.GetCurrentDate(),
          mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
          vehCount = result.vehicles.len(),
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                               + plan.economics.profitAnnual);
        OpexSign(anchor, "AH|" + this._nextLineId + "|"
                         + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                         + plan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
        OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        this._nextLineId++;
        return { outcome = "built", discards = passDiscards };
      }

  return { outcome = "rejected", discards = passDiscards };
}


/* C38 etape 2 : tentative synchrone route, y compris les gardes feeder et le siting vivant. */
function OpexAI::_tryBuildRoadProject(year, project, rank, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = project.src, dst = project.dst, reason = "road_disabled", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local candidate = project.payload;
      local isFeeder = ("isFeeder" in candidate) && candidate.isFeeder;
      if (candidate.kind == "pax") {
        local alreadyServed = false;
        if (FEEDER_UNLOCK && isFeeder) {
          local maxFeeders = 1;
          local isHubTown = ("isHubTown" in candidate) ? candidate.isHubTown : false;
          if (isHubTown && FEEDER_TOWN_COVERAGE) {
            local tId = ("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(candidate.src);
            local houses = AITown.IsValidTown(tId) ? AITown.GetHouseCount(tId) : 0;
            if (houses <= 0 && AITown.IsValidTown(tId)) houses = AITown.GetPopulation(tId) / 25;
            maxFeeders = OpexCeilDiv(houses, ROAD_STOP_CATCHMENT_HOUSES);
            if (maxFeeders > 4) maxFeeders = 4;
            if (maxFeeders < 1) maxFeeders = 1;
          }
          local currentCount = OpexTownFeederCount(this._lines, candidate.src, candidate.hubStationId);
          local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
          local yearsElapsed = (this._startYear >= 0) ? (year - this._startYear) : 0;
          if (currentCount >= maxFeeders || (slot >= 1 && yearsElapsed < 2)) {
            alreadyServed = true;
          }
        } else {
          alreadyServed = OpexRoadPairServed(this._lines, candidate.src, candidate.dst);
        }
        if (alreadyServed) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "pair_already_served", extra = "" });
          local abandonedKey = OpexAbandonedPairKey(candidate);
          this._markPairAbandoned(abandonedKey);
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexTownRoadLineCount(this._lines, candidate.src) >= 4) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!isFeeder && OpexTownRoadLineCount(this._lines, candidate.dst) >= 4) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else {
        if (OpexOriginServed(this._lines, candidate.src, true)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "src_origin_served", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexOriginServed(this._lines, candidate.dst, true)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "dst_origin_served", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|R|" + project.budgetScore + "|" + project.opcodeScore);

      this._budget.begin();
      local planning = OpexRoadPlanFor(this._catalog, candidate);
      local planOps = this._budget.end("build_road_plans");
      local plan = planning.plan;
      local idx = this._nextLineId;
      if (plan == null) {
        if (C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "plan_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=plan_failed detail=" + planning.reason);
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
        OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
      if (actualDist < 1) actualDist = 1;
      local economics = OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,
                                              candidate.monthly, candidate.engine, candidate.kind,
                                              plan.routeDistance);
      if (economics == null || (!isFeeder && economics.profitAnnual <= 0)) {
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=unprofitable_after_siting");
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|ECON|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      local netProfit = ("networkProfit" in candidate) ? candidate.networkProfit : 0;
      local netRev = ("networkRevenue" in candidate) ? candidate.networkRevenue : 0;
      OpexApplyRoadEconomics(candidate, economics, actualDist);
      if (netProfit > 0) {
        candidate.profitAnnual += netProfit;
        candidate.revenueAnnual += netRev;
        if (candidate.capital > 0) {
          candidate.roi = (candidate.profitAnnual * 1000) / candidate.capital;
        }
      }
      local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
      OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|" + result.opcodes);
      if (ROAD_COST_PROBE) {
        OpexSign(anchor, "RP|" + idx + "|" + result.plannedCapital + "|" + result.actualCost
                               + "|" + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "build_failed", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
        return { outcome = "rejected", discards = passDiscards };
      }

      if (DECISION_LOG) {
        foreach (d in passDiscards) {
          OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
        }
        passDiscards = [];
        local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
        OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=road kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi);
        OpexDecide("ROAD_BUILD", "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + result.cost + " vehicles=" + result.vehicles.len());
      }

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
      OpexSign(anchor, "RC|" + yy + "|" + idx + "|1|" + result.cost
                               + "|" + result.vehicles.len());
      /* Un feeder est une ligne routiere de RABATTAGE vers un hub rail ou aerien
       * (candidates.nut:1156), avec ordre OF_TRANSFER au hub. Rien ne le distinguait
       * d'une liaison ville-a-ville dans la telemetrie : impossible de dire si un seul avait
       * jamais ete bati. Un panneau par feeder, donc aucun cout quand il n'y en a pas. */
      if (("isFeeder" in candidate) && candidate.isFeeder) {
        OpexSign(anchor, "FE|" + idx + "|"
                                 + ((("hubMode" in candidate) && candidate.hubMode == "air") ? "A" : "T")
                                 + "|" + ((("joinedHub" in result) && result.joinedHub) ? 1 : 0));
      }
      if (ROAD_MULTISTOP) {
        OpexSign(anchor, "RM|" + yy + "|" + idx + "|1|"
                                 + result.nStopsA + "|" + result.nStopsB + "|"
                                 + result.vehicles.len());
      }
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
        mode = "road", kind = candidate.kind, depot = result.depot,
        nStopsA = result.nStopsA, nStopsB = result.nStopsB,
        capacity = ("capacity" in result) ? result.capacity : 25,
        srcIndustry = (candidate.kind == "freight" && candidate.srcTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.src) : -1,
        dstIndustry = (candidate.kind == "freight" && candidate.dstTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.dst) : -1,
        deadStreak = 0, scrapping = false, scrapVehicles = [],
        isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
        opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
        purpose = (("isFeeder" in candidate) && candidate.isFeeder) ? "feeder" : "profit",
        isFeeder = (("isFeeder" in candidate) && candidate.isFeeder),
        hubStationId = (("hubStationId" in candidate) ? candidate.hubStationId : -1),
        lineId = idx,
      });
      this._nextLineId++;
      return { outcome = "built", discards = passDiscards };

  return { outcome = "rejected", discards = passDiscards };
}

function OpexAI::_refreshDynamicBatch(year)
{
  local before = (this._projects != null && ("capitalBudget" in this._projects))
      ? this._projects.capitalBudget : OpexAvailableCapital();
  local after = OpexAvailableCapital();
  this._projects = OpexDynamicBatchReselect(this._projects, this._lines,
      this._dynamicBatch.attempted, after, this._abandonedPairs);
  this._ranked = this._projects.rail;
  local remaining = this._projects.best.len();
  if (DECISION_LOG) {
    OpexDecide("DYNAMIC_BATCH", "action=continue reason=success built="
               + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
               + " budget_before=" + before + " budget_after=" + after
               + " remaining=" + remaining);
  }
}

function OpexAI::_dynamicBatchBuilt(year)
{
  this._dynamicBatch.built++;
  this._dynamicBatch.consecutiveRejects = 0;
  this._refreshDynamicBatch(year);
}

/* P2 : seul un refus effectivement tente compte. Une recherche rail pending
 * rend la main sans appeler ce helper ; un succes remet la serie a zero. */
function OpexAI::_dynamicBatchRejected()
{
  if (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch == null) return false;
  this._dynamicBatch.consecutiveRejects++;
  if (DYNAMIC_BATCH_REJECT_LIMIT > 0
      && this._dynamicBatch.consecutiveRejects >= DYNAMIC_BATCH_REJECT_LIMIT) {
    this._dynamicBatch.stopReason = "consecutive_rejects";
    return true;
  }
  return false;
}

function OpexAI::_stopDynamicBatch(reason, year)
{
  if (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch == null) return;
  local after = OpexAvailableCapital();
  local remaining = (this._projects != null && ("best" in this._projects))
      ? this._projects.best.len() : 0;
  if (DECISION_LOG) {
    OpexDecide("DYNAMIC_BATCH", "action=stop reason=" + reason + " built="
               + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
               + " rejects=" + this._dynamicBatch.consecutiveRejects
               + " ops_floor=" + this._dynamicBatch.opsFloor
               + " budget_before=" + this._dynamicBatch.initialBudget + " budget_after=" + after
               + " remaining=" + remaining);
  }
  local built = this._dynamicBatch.built;
  if (this._projects != null) {
    if (this._dynamicBatch.sourceCandidateGroups != null) {
      this._projects.candidateGroups = this._dynamicBatch.sourceCandidateGroups;
    }
    if (this._dynamicBatch.sourceBudgetCandidates != null) {
      this._projects.budgetCandidates = this._dynamicBatch.sourceBudgetCandidates;
    }
  }
  this._dynamicBatch = null;
  /* Le filtre attempted mutile volontairement le vivier de travail. Une reconstruction
   * incrementale unique a la cloture restaure les candidats encore valides pour le cycle
   * suivant, sans liste noire persistante. */
  if (built > 0 && this._projects != null) {
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      fleetPlan = [];
      this._resizeAirFleets(year, fleetPlan);
    }
    this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget,
        this._lines, OpexAvailableCapital(), fleetPlan, this._abandonedPairs);
    this._ranked = this._projects.rail;
  }
}


/* C39.5 : conserve, par cle stable, le premier jour de la fenetre courante ou un projet du
 * vivier est finançable. La table neuve purge les projets sortis du vivier et borne la memoire.
 *
 * C39.5b : chaque valeur est desormais une table {since, topSince, turns, topTurns} au lieu
 * d'une date seule, pour separer les trois causes du delai D2 (cadence / file par rang /
 * concurrence caisse) :
 *   - since    : date du premier jour finançable (comportement d'origine, inchange) ;
 *   - topSince : date du premier jour ou ce projet etait le MEILLEUR projet finançable, i.e. le
 *                premier de this._projects.best (indice le plus bas) dont capital <= available ;
 *                -1 tant qu'il ne l'a jamais ete. Meme definition que bestRank de C41.48
 *                (C41_RAIL_DOMINATION_PROBE) : rester comparable entre les deux sondes ;
 *   - turns / topTurns : nombre de dispatches de la tache `projects` observes depuis since /
 *                topSince. Incrementes uniquement quand isProjectsTurn est vrai, pour ne compter
 *                que les tours de `projects` et pas l'appel fait depuis la tache `catalog`
 *                (qui, lui, ne fait qu'horodater since/topSince avant le premier tour utile).
 *
 * capital : optionnel. L'appelant du site de dispatch de `projects` a deja calcule
 * OpexAvailableCapital() pour sa propre ligne de journal (capital=) ; le lui laisser passer evite
 * de le recalculer ici. L'appel depuis la tache `catalog` (qui n'emet aucun log) continue de le
 * calculer lui-meme en laissant capital a null. */
function OpexAI::_c39StampFinanceable(capital = null, isProjectsTurn = false)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return 0;
  local available = (capital != null) ? capital : OpexAvailableCapital();
  local date = AIDate.GetCurrentDate();
  local stamped = {};
  local topFound = false;
  if (this._projects != null && this._projects.best != null) {
    local limit = this._projects.best.len() < 64 ? this._projects.best.len() : 64;
    for (local i = 0; i < limit; i++) {
      local project = this._projects.best[i];
      if (project == null || project.capital > available) continue;
      local isTop = !topFound;
      topFound = true;
      local key = OpexProjectAttemptKey(project);
      local prev = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
      local since = (prev != null) ? prev.since : date;
      local topSince = (prev != null) ? prev.topSince : -1;
      if (isTop && topSince == -1) topSince = date;
      local turns = (prev != null) ? prev.turns : 0;
      local topTurns = (prev != null) ? prev.topTurns : 0;
      if (isProjectsTurn) {
        turns++;
        if (isTop) topTurns++;
      }
      stamped[key] <- { since = since, topSince = topSince, turns = turns, topTurns = topTurns };
    }
  }
  this._c39FinanceableSince = stamped;
  return stamped.len();
}

function OpexAI::_tryBuildProjects(year)
{
  local c49Best = null;
  local c49BuiltRanks = null;
  local c49AttemptedRanks = null;
  local c48PassMark = null;
  local c48BestLen = 0;
  local c48MaxRank = -1;
  local c48AttemptsTotal = 0;
  local c48BuiltThisPass = false;
  if (C48_PROJECT_ATTEMPT_LEDGER) {
    c48PassMark = OpexOpsMeasureBegin();
    c48BestLen = (this._projects != null && this._projects.best != null)
        ? this._projects.best.len() : 0;
  }
  /* C38 : l'etat ne nait que pour le bras experimental. Il survivra a un A* suspendu ; le
   * bras livre ne fait aucune allocation ni lecture supplementaire. */
  if (PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch == null) {
    this._dynamicBatch = {
      attempted = {}, attemptedCount = 0, built = 0,
      consecutiveRejects = 0,
      initialBudget = OpexAvailableCapital(), opsFloor = DYNAMIC_BATCH_OPS_FLOOR,
      stopReason = null, pendingLogged = false,
      sourceCandidateGroups = (this._projects != null && ("candidateGroups" in this._projects))
          ? this._projects.candidateGroups : null,
      sourceBudgetCandidates = (this._projects != null && ("budgetCandidates" in this._projects))
          ? this._projects.budgetCandidates : null,
    };
  }
  /* G4§1 : le drapeau peut etre pose entre deux passes par _consumeRailSearch.
   * Ne pas le remettre a zero ici : la passe suivante doit alors re-elire le
   * portefeuille avec la nouvelle memoire d'abandon. */
  if (PORTFOLIO_FRESH_BUDGET && this._projects != null) {
    local initialBudget = this._projects.generationCapitalBudget;
    local budgetNow = OpexAvailableCapital();
    this._projects = OpexReselectProjects(this._projects, budgetNow);
    /* 30 caracteres au pire : FB|99|2147483647|2147483647|64. */
    OpexSign(AIMap.GetTileIndex(1, 1), "FB|" + (year % 100) + "|" + initialBudget
             + "|" + budgetNow + "|" + this._projects.stats.budgetSelected);
  }
  if (C49_SCARCITY_LEDGER) {
    c49Best = (this._projects != null && this._projects.best != null) ? this._projects.best : null;
    c49BuiltRanks = {};
    c49AttemptedRanks = {};
  }
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  local builtCount = 0;
  local passDiscards = [];
  /* P2 : fractionner le tick. Le plancher historique protege toujours les
   * autres taches quand le pourcentage est nul ou que le tick est deja court. */
  local dynamicOpsFloor = DYNAMIC_BATCH_OPS_FLOOR;
  if (PORTFOLIO_DYNAMIC_BATCH && DYNAMIC_BATCH_OPS_BUDGET_PCT > 0) {
    local opsNow = AIController.GetOpsTillSuspend();
    local reserved = (opsNow * (100 - DYNAMIC_BATCH_OPS_BUDGET_PCT)) / 100;
    if (reserved > dynamicOpsFloor) dynamicOpsFloor = reserved;
  }
  if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatch.opsFloor = dynamicOpsFloor;
  /* 1 conserve le break historique. Au-dela, chaque candidat apres le premier succes passe les
   * revalidations de son mode contre this._lines, la carte et la tresorerie vivantes. */
  local maxBatch = PORTFOLIO_MAX_BATCH;

  /* C41.49 : meme garde que C41.48 (kind=="primary", phase=="search") -- la sonde ne regarde
   * que la fenetre ou l'A* rail est en vol, pas la phase "build" (deja couverte par
   * _consumeRailSearch/C41.47) ni un upgrade. Rien n'est coupe : fallthroughAttempted/Built
   * comptent ce que la boucle ci-dessous fait DEJA des candidats non-rail. */
  local fallthroughProbeActive = C41_PROJECTS_FALLTHROUGH_PROBE && this._railSearch != null
      && this._railSearch.kind == "primary" && this._railSearch.phase == "search";
  local fallthroughAttempted = 0;
  local fallthroughBuilt = 0;
  if (fallthroughProbeActive) {
    OpexC41ProjectsFallthroughLog("phase=entry invalidated="
        + (this._portfolioInvalidated ? 1 : 0) + " best_len="
        + ((this._projects != null) ? this._projects.best.len() : -1));
  }

  /* A4 : un A* termine au tour precedent a depose un railPlan sur le candidat stocke. On le
   * consomme AVANT le balayage du portefeuille, qui a pu etre regenere entre-temps. */
  if (PORTFOLIO_DYNAMIC_BATCH && RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase != "build") {
    if (DECISION_LOG && !this._dynamicBatch.pendingLogged) {
      this._dynamicBatch.pendingLogged = true;
      OpexDecide("DYNAMIC_BATCH", "action=stop reason=rail_pending built="
                 + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
                 + " budget_before=" + this._dynamicBatch.initialBudget + " budget_after="
                 + OpexAvailableCapital() + " remaining=" + this._projects.best.len());
    }
    if (C48_PROJECT_ATTEMPT_LEDGER) {
      this._recordC48PassLedger(c48AttemptsTotal, OpexOpsMeasureEnd(c48PassMark),
          c48BuiltThisPass, c48BestLen, c48MaxRank);
    }
    if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
    return true;
  }
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase == "build") {
    local outcome = this._consumeRailSearch(year);
    /* Atteignable seulement avec portfolio_dynamic_batch=1 (non-defaut) : conserver le ledger. */
    if (PORTFOLIO_DYNAMIC_BATCH && outcome == "cash") {
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        this._recordC48PassLedger(c48AttemptsTotal, OpexOpsMeasureEnd(c48PassMark),
            c48BuiltThisPass, c48BestLen, c48MaxRank);
      }
      if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
      return true;
    }
    if (outcome != "cash") {
      if (C39_PROJECTS_CADENCE_PROBE && outcome == "built") {
        local railCandidate = this._railSearch.candidate;
        /* railCandidate est le payload brut, pas le projet : il n'a pas de slot mode, donc
         * OpexProjectAttemptKey() produirait la cle incompatible unknown|... au lieu de rail|.... */
        local key = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
            + railCandidate.cargo + "|" + railCandidate.kind;
        local railRank = -1;
        if (this._projects != null && this._projects.best != null) {
          for (local i = 0; i < this._projects.best.len(); i++) {
            local project = this._projects.best[i];
            if (project != null && OpexProjectAttemptKey(project) == key) {
              railRank = i;
              break;
            }
          }
        }
        /* C39.5b : meme forme d'entry que les 5 sites generiques ; la cle reste construite a la
         * main (commentaire ci-dessus), seul le contenu lu change. */
        local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
        local daysSinceFinanceable = (entry != null)
            ? AIDate.GetCurrentDate() - entry.since : -1;
        local daysSinceTop = (entry != null && entry.topSince != -1)
            ? AIDate.GetCurrentDate() - entry.topSince : -1;
        local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
        local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
        OpexC39ProjectsCadenceLog("phase=built mode=rail rank=" + railRank
            + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
            + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
            + " rail_search=1 capital_after=" + OpexAvailableCapital());
      }
      local c49RailCandidate = C49_SCARCITY_LEDGER ? this._railSearch.candidate : null;
      if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatch.pendingLogged = false;
      this._railSearch = null;
      if (outcome == "built") {
        builtCount++;
        if (C49_SCARCITY_LEDGER && c49Best != null) {
          local railCandidate = c49RailCandidate;
          for (local i = 0; i < c49Best.len(); i++) {
            local project = c49Best[i];
            if (project != null && project.mode == "rail" && project.payload.src == railCandidate.src
                && project.payload.dst == railCandidate.dst && project.payload.cargo == railCandidate.cargo
                && project.payload.kind == railCandidate.kind) {
              c49BuiltRanks.rawset(i, true);
              break;
            }
          }
        }
        if (C48_PROJECT_ATTEMPT_LEDGER) c48BuiltThisPass = true;
        if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatchBuilt(year);
      } else if (PORTFOLIO_DYNAMIC_BATCH && outcome == "failed") {
        this._dynamicBatchRejected();
      }
    }
  }

  if ((PORTFOLIO_DYNAMIC_BATCH || builtCount < maxBatch)
      && this._projects != null && this._projects.best.len() > 0
      && (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch.stopReason == null)) {
  local logDiscardsThisPass = false;
  /* Le calcul du mois courant coute DEUX appels d'API et tournait a chaque passage, reglage
   * eteint compris. Ici le comportement depend des opcodes consommes : tout ce qui ne sert
   * qu'a journaliser doit vivre DANS la garde, pas seulement l'appel a OpexDecide. */
  if (DECISION_LOG) {
    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    if (_lastProjectScanMonth != ym) {
      _lastProjectScanMonth = ym;
      logDiscardsThisPass = true;
    }
  }
  for (local i = 0; i < this._projects.best.len(); i++) {
    local project = this._projects.best[i];
    if (project == null) continue;

    if (PORTFOLIO_DYNAMIC_BATCH) {
      if (AIController.GetOpsTillSuspend() < dynamicOpsFloor) {
        this._dynamicBatch.stopReason = "opcode_budget";
        break;
      }
      local projectKey = OpexProjectAttemptKey(project);
      if (projectKey in this._dynamicBatch.attempted) continue;
      this._dynamicBatch.attempted[projectKey] <- true;
      this._dynamicBatch.attemptedCount++;
    }

    local mode = project.mode;
    local modeChar = mode == "rail" ? "T" : (mode == "road" ? "R" : (mode == "air" ? "A" : "W"));
    local liveBuiltCount = PORTFOLIO_DYNAMIC_BATCH ? this._dynamicBatch.built : builtCount;
    if (C48_PROJECT_ATTEMPT_LEDGER && i > c48MaxRank) c48MaxRank = i;

    if (mode == "fleet") {
      local attempt = null;
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        local attemptDate = AIDate.GetCurrentDate();
        local attemptMark = OpexOpsMeasureBegin();
        attempt = this._tryBuildFleetProject(year, project, i, passDiscards);
        this._recordC48AttemptLedger("fleet", attempt.outcome, i,
            OpexOpsMeasureEnd(attemptMark), AIDate.GetCurrentDate() - attemptDate);
        c48AttemptsTotal++;
        if (attempt.outcome == "built") c48BuiltThisPass = true;
      } else attempt = this._tryBuildFleetProject(year, project, i, passDiscards);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        builtCount++;
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt(year);
          i = -1;
        } else if (builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
      continue;
    }

    if (mode == "air") {
      local attempt = null;
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        local attemptDate = AIDate.GetCurrentDate();
        local attemptMark = OpexOpsMeasureBegin();
        attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,
                                           anchor, yy);
        this._recordC48AttemptLedger("air", attempt.outcome, i,
            OpexOpsMeasureEnd(attemptMark), AIDate.GetCurrentDate() - attemptDate);
        c48AttemptsTotal++;
        if (attempt.outcome == "built") c48BuiltThisPass = true;
      } else attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,
                                                 anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        builtCount++;
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt(year);
          i = -1;
        } else if (builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "road") {
      local attempt = null;
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        local attemptDate = AIDate.GetCurrentDate();
        local attemptMark = OpexOpsMeasureBegin();
        attempt = this._tryBuildRoadProject(year, project, i, passDiscards, anchor, yy);
        this._recordC48AttemptLedger("road", attempt.outcome, i,
            OpexOpsMeasureEnd(attemptMark), AIDate.GetCurrentDate() - attemptDate);
        c48AttemptsTotal++;
        if (attempt.outcome == "built") c48BuiltThisPass = true;
      } else attempt = this._tryBuildRoadProject(year, project, i, passDiscards, anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        builtCount++;
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt(year);
          i = -1;
        } else if (builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "rail") {
      local attempt = null;
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        local attemptDate = AIDate.GetCurrentDate();
        local attemptMark = OpexOpsMeasureBegin();
        attempt = this._tryBuildRailProject(year, project, i, liveBuiltCount, passDiscards,
                                            anchor, yy);
        this._recordC48AttemptLedger("rail", attempt.outcome, i,
            OpexOpsMeasureEnd(attemptMark), AIDate.GetCurrentDate() - attemptDate);
        c48AttemptsTotal++;
        if (attempt.outcome == "built") c48BuiltThisPass = true;
      } else attempt = this._tryBuildRailProject(year, project, i, liveBuiltCount, passDiscards,
                                                  anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (attempt.outcome == "pending") {
        /* En batch historique > 1, le portefeuille doit etre regenere avant de reprendre un
         * A* suspendu. Le defaut unitaire conserve le retour immediat d'origine. */
        if (!PORTFOLIO_DYNAMIC_BATCH && builtCount > 0) break;
        if (C48_PROJECT_ATTEMPT_LEDGER) {
          this._recordC48PassLedger(c48AttemptsTotal, OpexOpsMeasureEnd(c48PassMark),
              c48BuiltThisPass, c48BestLen, c48MaxRank);
        }
        if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
        return true;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        builtCount++;
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt(year);
          i = -1;
        } else if (builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "water") {
      local attempt = null;
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      if (C48_PROJECT_ATTEMPT_LEDGER) {
        local attemptDate = AIDate.GetCurrentDate();
        local attemptMark = OpexOpsMeasureBegin();
        attempt = this._tryBuildWaterProject(year, project, i, liveBuiltCount, passDiscards,
                                             anchor, yy);
        this._recordC48AttemptLedger("water", attempt.outcome, i,
            OpexOpsMeasureEnd(attemptMark), AIDate.GetCurrentDate() - attemptDate);
        c48AttemptsTotal++;
        if (attempt.outcome == "built") c48BuiltThisPass = true;
      } else attempt = this._tryBuildWaterProject(year, project, i, liveBuiltCount, passDiscards,
                                                   anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        builtCount++;
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt(year);
          i = -1;
        } else if (builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    }
  }
  if (fallthroughProbeActive) {
    OpexC41ProjectsFallthroughLog("phase=exit invalidated="
        + (this._portfolioInvalidated ? 1 : 0) + " attempted=" + fallthroughAttempted
        + " built=" + fallthroughBuilt);
  }
  if (DECISION_LOG && builtCount == 0 && logDiscardsThisPass && passDiscards.len() > 0) {
    local maxLog = passDiscards.len() < 3 ? passDiscards.len() : 3;
    for (local k = 0; k < maxLog; k++) {
      local d = passDiscards[k];
      OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
    }
  }
  }

  if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);

  /* G4§1 : l'ancien chemin deduisait hadAbandons de passDiscards, dont le remplissage
   * est garde par DECISION_LOG (defaut 0). Le drapeau _hadAbandonsThisPass est pose
   * directement par _markPairAbandoned, couvrant tous les chemins (air, route, rail
   * bloquant et reprenable via _consumeRailSearch). */
  local hadAbandons = this._hadAbandonsThisPass;
  local batchBuilt = PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch != null
      ? this._dynamicBatch.built : builtCount;

  if (builtCount > 0 || hadAbandons || batchBuilt > 0) {
    local fleetPlan = null;
    if (!PORTFOLIO_DYNAMIC_BATCH && FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (PORTFOLIO_DYNAMIC_BATCH && batchBuilt > 0) {
      /* Chaque succes a deja filtre et re-classe sur le budget vivant. */
    } else if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
      this._rebuildProjects(fleetPlan);
    } else if (PORTFOLIO_CACHE && this._projects != null && (("budgetCandidates" in this._projects) || ("candidateGroups" in this._projects))) {
      local budgetNow = OpexAvailableCapital();

      this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs);
    } else {
      this._rebuildProjects(fleetPlan);
    }
    this._ranked = this._projects.rail;
    if (PORTFOLIO_LOG) OpexLogPortfolioRank(this._projects);
    /* `knapsackExact` et le compteur d'imbrications du budget etaient ECRITS ET LUS NULLE PART.
     * Or maxNodes = 2000 pour n = 64 fait tronquer la recherche couramment : sans ce champ, on ne
     * peut pas distinguer « le solveur a prouve l'optimum » de « il a epuise son budget de noeuds »
     * -- l'angle mort qui a laisse survivre quatre defauts du portefeuille (docs/taches.md
     * S0 septies). Ajoutes au panneau EXISTANT plutot que dans un nouveau : un appel BuildSign de
     * plus deplace les frontieres de ticks (precedent mesure : un helper devant 57 appels a coute
     * 3 lignes rail). Longueur maximale d'un panneau : 31 caracteres. */
    OpexSign(anchor, "IG|" + yy + "|" + this._projects.stats.modeCandidates + "|"
             + this._projects.stats.odProjects + "|" + this._projects.stats.budgetSelected
             + "|" + (this._projects.stats.knapsackExact ? 0 : 1)
             + "|" + this._budget.nested);
    /* air_fleet_probe : combien de hubs le rabattage voit-il, et combien de candidats feeders
     * en tire-t-il ? Sans ces deux nombres, un "zero feeder bati" ne dit pas si la generation
     * est vide ou si l'election les ecarte. */
    if (AIR_FLEET_PROBE && ("road" in this._projects) && ("stats" in this._projects.road) &&
        ("feederCandidates" in this._projects.road.stats)) {
      OpexSign(anchor, "FN|" + yy + "|" + this._projects.road.stats.feederHubs
                             + "|" + this._projects.road.stats.feederCandidates);
    }
    /* B est le nombre reellement construit dans CE passage. On complete IB au lieu d'ajouter un
     * panneau : ses deux champs historiques restent aux memes positions, et avec les deux
     * capitaux a 10 chiffres que le format IB admet deja, |B8 fait 30 caracteres, sous 31. */
    OpexSign(anchor, "IB|" + yy + "|" + this._projects.capitalBudget + "|"
             + this._projects.stats.selectedCapital + "|B" + batchBuilt);
    /* L'abandon a maintenant ete consomme par la reelection/reconstruction. */
    if (hadAbandons) this._hadAbandonsThisPass = false;
    if (PORTFOLIO_DYNAMIC_BATCH) {
      local reason = this._dynamicBatch.stopReason != null
          ? this._dynamicBatch.stopReason : "no_financeable";
      this._stopDynamicBatch(reason, year);
    }
    if (C48_PROJECT_ATTEMPT_LEDGER) {
      this._recordC48PassLedger(c48AttemptsTotal, OpexOpsMeasureEnd(c48PassMark),
          c48BuiltThisPass, c48BestLen, c48MaxRank);
    }
    return true;
  }
  if (PORTFOLIO_DYNAMIC_BATCH) {
    local reason = this._dynamicBatch.stopReason != null
        ? this._dynamicBatch.stopReason : "no_success";
    this._stopDynamicBatch(reason, year);
  }
  if (C48_PROJECT_ATTEMPT_LEDGER) {
    this._recordC48PassLedger(c48AttemptsTotal, OpexOpsMeasureEnd(c48PassMark),
        c48BuiltThisPass, c48BestLen, c48MaxRank);
  }
  return false;
}

/* Item 7 : au plus UNE tentative rail par an sur une paire que le modele a rejetee
 * (profit predit <= 0). Le classement n'en a jamais vu : stash des moins negatives,
 * hors TOP_K. On ne joint pas, on n'emprunte pas.
 *
 * Budget : alternativeRatio 0, chemin Z, HARD_ITERATION_CAP (40 000). Le premier
 * sondage (results/opex_probe_negative_20y_5seeds.json) passait MIN_RATIO et tombait
 * au plancher 2000 : 48/52 ABND, mediane 123 tuiles. Le volume des rejets est le
 * long ; 2000 ne le mesure pas. 0 n'ajoute aucun parametre a OpexBuildLine, donc
 * le chemin d'opcodes du classement reste intact.
 *
 * Panneaux, tous gates par probe_negative donc absents du defaut :
 *  PQ|aa|stash|close|cash|tried  -- entonnoir annuel
 *  PN|aa|id|profit|dist|R|iter   -- la tentative, profit AU CLASSEMENT (celui du rejet)
 *  PX|id                         -- la ligne batie est un probe, pas un candidat classe
 * Pire PN|99|999|-999999|200|A|40000 : 29 caracteres. */
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
    local vehicleType = OpexLineVehicleType(line);
    /* fleet_fix : ce `continue` sautait la ligne AVANT toute mise a jour de deadStreak, vehCount,
     * lastProfit, lastRevenue et lastLiveVehicles. Une gare A devenue invalide (demolie, tuile
     * passee a autrui) gelait donc l'etat de la ligne POUR TOUJOURS : _scrapDeadLines s'appuyant
     * sur deadStreak, la ligne n'etait jamais ferraillee, ses vehicules saignaient leur cout
     * d'exploitation toute la partie, et ses deux extremites continuaient de bloquer _tooClose
     * pour de nouveaux candidats (docs/taches.md S0 nonies). Meme mode d'echec que la ligne OIL_
     * deja documentee plus bas, sur un chemin que ce correctif ne couvrait pas.
     *
     * On compte desormais la gare perdue comme une annee morte : la ligne rejoint le chemin normal
     * de ferraillage au lieu de pourrir en silence. */
    if (!AIStation.IsValidStation(stationA)) {
      if (FLEET_FIX || vehicleType == AIVehicle.VT_AIR) {
        local streak = ("deadStreak" in line) ? line.deadStreak : 0;
        line.deadStreak <- streak + 1;
        if (!("scrapping" in line)) line.scrapping <- false;
        if (!("scrapVehicles" in line)) line.scrapVehicles <- [];
        OpexSign(anchor, "OZ|" + line.lineId + "|" + year + "|SA|" + line.deadStreak);
      }
      continue;
    }

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
    local roadRealSpeed = -1;
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
      if (moving.len() > 0) roadRealSpeed = OpexMedianInt(moving);
      OpexSign(anchor, "RY|" + (year % 100) + "|" + line.lineId + "|" + kindCh + "|"
                               + moving.len() + "|" + (roadRealSpeed >= 0 ? roadRealSpeed : 0) + "|"
                               + pred + "|" + cat);
    }
    /* `<-` : le slot n'existe pas a la construction. `=` leve "the index 'vehCount' does not
     * exist" et tue le script (mesure 2026-08-29, toutes les graines, des 1971). */
    line.vehCount <- vehCount;
    line.lastProfit <- profit;
    line.lastRevenue <- profit + runCost;
    if (DECISION_LOG) {
      local realRevenue = profit + runCost;
      local predRevenue = ("predRevenue" in line) ? line.predRevenue : 0;
      local predProfit = ("predicted" in line) ? line.predicted : 0;
      local predRunning = ("predRunning" in line) ? line.predRunning : 0;
      local isLow = ("isLowRatio" in line && line.isLowRatio) ? 1 : 0;
      local opRatio = ("opcodeRatio" in line) ? line.opcodeRatio : -1;
      local lMode = ("mode" in line) ? line.mode : "unknown";
      local lKind = ("kind" in line) ? line.kind : "unknown";
      local lAge = ("year" in line) ? (year - line.year) : -1;
      local lPurpose = ("purpose" in line) ? line.purpose : "profit";
      local cLabel = AICargo.GetCargoLabel(line.cargo);
      local extra = "";
      if (lMode == "road") {
        local predVehs = ("predTrains" in line) ? line.predTrains : 0;
        local predCarried = ("predCarried" in line) ? line.predCarried : 0;
        local predDays = ("predOneWayDays" in line) ? line.predOneWayDays : 0;
        local predDist = ("distance" in line) ? line.distance : 0;
        local predSpeed = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
        local catSpeed = ("catalogSpeed" in line) ? line.catalogSpeed : 0;
        local realDist = (AIStation.IsValidStation(stationA) && AIStation.IsValidStation(stationB))
            ? AIMap.DistanceManhattan(AIStation.GetLocation(stationA), AIStation.GetLocation(stationB)) : predDist;
        local townA = ("originA" in line) ? AITile.GetClosestTown(line.originA) : -1;
        local townB = ("originB" in line) ? AITile.GetClosestTown(line.originB) : -1;
        local popA = AITown.IsValidTown(townA) ? AITown.GetPopulation(townA) : -1;
        local popB = AITown.IsValidTown(townB) ? AITown.GetPopulation(townB) : -1;
        local prodA = AITown.IsValidTown(townA) ? AITown.GetLastMonthProduction(townA, line.cargo) : -1;
        local prodB = AITown.IsValidTown(townB) ? AITown.GetLastMonthProduction(townB, line.cargo) : -1;
        local waitA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : -1;
        local waitB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : -1;
        local cap = ("capacity" in line) ? line.capacity : -1;
        extra = " pred_vehs=" + predVehs + " dist=" + predDist + " real_dist=" + realDist
              + " pred_carried=" + predCarried + " pred_days=" + predDays + " pred_speed=" + predSpeed
              + " cat_speed=" + catSpeed + " real_speed=" + roadRealSpeed + " rating_a=" + ratingA
              + " rating_b=" + ratingB + " pop_a=" + popA + " pop_b=" + popB + " prod_a=" + prodA
              + " prod_b=" + prodB + " wait_a=" + waitA + " wait_b=" + waitB + " cap=" + cap;
      }
      OpexDecide("LINE_REVENUE", "line=" + line.lineId + " mode=" + lMode + " kind=" + lKind + " cargo=" + cLabel + " year=" + year + " age=" + lAge + " pred_rev=" + predRevenue + " real_rev=" + realRevenue + " pred_prof=" + predProfit + " real_prof=" + profit + " pred_run=" + predRunning + " real_run=" + runCost + " vehs=" + vehCount + " low_ratio=" + isLow + " op_ratio=" + opRatio + " purpose=" + lPurpose + extra);
    }
    if (vehicleType == AIVehicle.VT_RAIL || vehicleType == AIVehicle.VT_AIR) {
      /* Instantane de backlog, complete par l'utilisation annuelle derivee du revenu dans
       * _expandRailLines. Le second signal evite que la phase du train au jour du releve fasse
       * disparaitre une saturation reelle ; deux annees consecutives restent obligatoires. */
      line.lastWaitingA <- AIStation.GetCargoWaiting(stationA, line.cargo);
      line.lastWaitingB <- AIStation.IsValidStation(stationB)
          ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
      if (vehicleType == AIVehicle.VT_AIR) {
        OpexSign(anchor, "FA|" + (year % 100) + "|" + line.lineId + "|"
                         + line.lastWaitingA + "|" + line.lastWaitingB);
      }
    }

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
    } else if (vehicleType == AIVehicle.VT_AIR) {
      /* G10 : une ligne air n'a pas de signal industrie. Son bilan annuel est donc la mesure
       * directe de sa viabilite. Deux pertes consecutives, comme le seuil fret, evitent de
       * vendre un appareil sur une seule annee de mise en route ou de fluctuation du trafic. */
      local priorStreak = ("deadStreak" in line) ? line.deadStreak : 0;
      local nextStreak = profit < 0 ? priorStreak + 1 : 0;
      if ("deadStreak" in line) line.deadStreak = nextStreak;
      else line.deadStreak <- nextStreak;
      if (!("scrapping" in line)) line.scrapping <- false;
      if (!("scrapVehicles" in line)) line.scrapVehicles <- [];
      if (nextStreak > 0) OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + nextStreak);
    }
  }
}

/* Dimensionnement progressif de l'air. Une prediction de population ne peut plus acheter une
 * flotte entiere au demarrage. Apres au moins une annee, on ajoute au plus UN avion par ligne et
 * par an si (1) les appareils existants gagnent de l'argent et (2) au moins une charge utile
 * complete attend dans les deux aeroports. Un echec de cash est reporte a l'annee suivante : la
 * file ne le resonde pas a chaque cycle et ne gaspille donc pas d'opcodes. */
/* Cause du refus de croissance d'une flotte aerienne, une seule fois par ligne et par an.
 * Codes : Y deja grandie cette annee, V aucun avion vivant, D ligne morte, L profit negatif,
 * C plafond physique de l'aeroport atteint, Q plafond de demande atteint,
 * S un an de mauvaise sante, M tresorerie, X l'achat a echoue. */
function OpexAirFleetRefusal(line, year, code)
{
  if (!AIR_FLEET_PROBE && !DECISION_LOG) return;
  if (!("lineId" in line)) return;
  /* rabattage_diag (2026-09-02) : dedup resserre au MOIS, pas a l'annee -- le dedup annuel
   * masquait un blocage de plusieurs mois derriere un seul motif fige au premier refus de
   * l'annee, alors que la tresorerie disponible changeait entre-temps. Diagnostic uniquement. */
  local month = AIDate.GetMonth(AIDate.GetCurrentDate());
  local ym = year * 12 + month;
  if (("lastFleetProbeMonth" in line) && line.lastFleetProbeMonth == ym) return;
  line.lastFleetProbeMonth <- ym;
  if (AIR_FLEET_PROBE) {
    OpexSign(AIMap.GetTileIndex(2, 10 + line.lineId),
             "FR|" + (year % 100) + (month < 10 ? "0" + month : "" + month) + "|" + line.lineId + "|" + code);
  }
  if (DECISION_LOG) {
    local yieldVal = OpexAirFleetYield(line);
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    local reasonStr = code;
    if (code == "Y") reasonStr = "already_grown_this_year";
    else if (code == "V") reasonStr = "no_live_aircraft";
    else if (code == "D") reasonStr = "dead_line";
    else if (code == "L") reasonStr = "negative_profit";
    else if (code == "C") reasonStr = "airport_capacity_reached";
    else if (code == "Q") reasonStr = "demand_cap_reached";
    else if (code == "S") reasonStr = "poor_health_streak";
    else if (code == "M") reasonStr = "insufficient_cash";
    else if (code == "X") reasonStr = "purchase_failed";
    OpexDecide("AIR_FLEET", "action=refuse line=" + line.lineId + " reason=" + reasonStr + " planes=" + have + " yield=" + yieldVal);
  }
}

/* Rendement marginal d'une ligne aerienne : profit PAR APPAREIL deja en service. C'est le
 * predicteur du remboursement de l'appareil SUIVANT -- une ligne qui gagne 100 k£ avec 2 avions
 * rembourse deux fois plus vite que celle qui gagne 100 k£ avec 8. `lastProfit` (mesure ecrite
 * par _reportLines) prime sur `predicted` (modele) des qu'il existe ; une ligne neuve jamais
 * rapportee tombe donc sur sa prevision plutot que sur zero, sinon elle serait servie en dernier
 * pendant toute sa premiere annee. */
function OpexAirFleetYield(line)
{
  local fleet = ("vehCount" in line) ? line.vehCount
              : (("vehicles" in line) ? line.vehicles.len() : 1);
  if (fleet < 1) fleet = 1;
  local profit = ("lastProfit" in line) ? line.lastProfit
               : (("predicted" in line) ? line.predicted : 0);
  return profit / fleet;
}

/* Comparateur de tete de file pour la croissance aerienne : meilleur rendement d'abord.
 * Fonction NOMMEE au niveau module, comme OpexFeederCandidateCompare : dans cet environnement
 * Squirrel une closure imbriquee ne capture jamais les locales englobantes. */
function OpexAirFleetPriorityCompare(a, b)
{
  local ya = OpexAirFleetYield(a);
  local yb = OpexAirFleetYield(b);
  if (ya > yb) return -1;
  if (ya < yb) return 1;
  return 0;
}

/* C34.2 : `plan` non nul = MODE A BLANC. La fonction traverse exactement les memes treize gardes
 * de refus, mais au lieu d'acheter elle enregistre ce qu'elle achererait dans `plan`, sous la forme
 * { line, want, planePrice }. C'est volontairement une reutilisation et non une extraction : les
 * gardes sont trop nombreuses et trop calibrees pour etre dupliquees sans divergence silencieuse.
 * Le portefeuille appelle ainsi la meme decision que la tache, puis l'arbitre contre les lignes
 * neuves au lieu de la servir d'office avant elles. */
function OpexAI::_resizeAirFleets(year, plan = null)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  /* air_roi_order : servir la ligne qui rembourse le plus vite, pas la plus ancienne. Le tri
   * porte sur une COPIE de references : _lines garde son ordre, dont depend l'indexation de
   * _scrapDeadLines (retrait par position). */
  local airLines = [];
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode == "air") airLines.append(line);
  }
  if (AIR_ROI_ORDER) airLines.sort(OpexAirFleetPriorityCompare);
  foreach (line in airLines) {
    /* C15 : Cadence d'extension de flotte aerienne.
     * Si AIR_FLEET_CADENCE_DAYS >= 365 : conservation exacte du verrou annuel historique.
     * Sinon : verrou glissant en jours depuis la derniere extension (ou la creation de la ligne). */
    if (AIR_FLEET_CADENCE_DAYS >= 365) {
      if (("lastAirFleetYear" in line) && line.lastAirFleetYear == year) { OpexAirFleetRefusal(line, year, "Y"); continue; }
    } else {
      local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate : (("buildDate" in line) ? line.buildDate : 0);
      if (lastDate > 0 && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS) {
        OpexAirFleetRefusal(line, year, "Y");
        continue;
      }
    }
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    if (have < 1) { OpexAirFleetRefusal(line, year, "V"); continue; }
    if (("deadStreak" in line) && line.deadStreak >= 2) { OpexAirFleetRefusal(line, year, "D"); continue; }

    // Condition 1 : Les appareils existants ne doivent pas etre deficitaires
    if (("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); continue; }

    /* marginal_fleet = 1 (2026-09-01) : dimensionnement marginal STRICT de l'air. Le commentaire
     * de cette fonction promettait deja d'attendre un an, d'exiger une charge complete en attente
     * et de ne jamais ajouter plus d'un avion par an -- mais rien ci-dessus ni ci-dessous ne
     * verifiait l'age de la ligne ou le fret en attente, et la boucle plus bas autorisait jusqu'a
     * 4 avions en un seul passage (addedThisPass < 4). Sous 0 (defaut), ce bloc ne change RIEN :
     * il ajoute seulement des refus supplementaires, jamais un chemin different pour les
     * conditions deja verifiees plus haut (have, deadStreak, lastProfit < 0). */
    if (MARGINAL_FLEET && AIR_FLEET_BUFFER < 0) {
      // (a) la ligne a au moins un an d'existence revolu
      if (!("year" in line) || (year - line.year) < 1) continue;
      // (b) lastProfit disponible ET strictement positif (pas seulement "pas negatif")
      if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
      // (c) au moins une capacite complete d'avion attend REELLEMENT dans une des deux gares
      local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
      if (planeCap <= 0) continue;
      /* Pas de AIStation.STATION_INVALID ici : jamais utilise ailleurs dans ce projet, on prefere
       * garder le meme garde-fou "hasB" que le reste du fichier (cf. lastWaitingB plus haut). */
      local stA = AIStation.GetStationID(line.stationA);
      local hasB = ("stationB" in line) && line.stationB != null;
      local stB = hasB ? AIStation.GetStationID(line.stationB) : 0;
      local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
      local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
      if (waitA < planeCap && waitB < planeCap) continue;
    }

    local isSmallAirport = false;
    if ((AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
        (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL)) {
      isSmallAirport = true;
    }
    local physicalMaxPlanes = isSmallAirport ? 4 : AIR_MAX_PLANES_PER_ROUTE;
    if (AIR_CADENCE_CAP) {
      physicalMaxPlanes = OpexAirCadenceCap(line, this._catalog, this._lines);
    }
    local maxPlanesForAirport = physicalMaxPlanes;
    if (have >= physicalMaxPlanes) { OpexAirFleetRefusal(line, year, "C"); continue; }
    if (AIR_DEMAND_CAP) {
      local demand = OpexAirDemandCap(line, this._catalog, this._lines);
      if (demand.cap < maxPlanesForAirport) maxPlanesForAirport = demand.cap;
      if (DECISION_LOG) {
        OpexDecide("AIR_DEMAND_CAP", "line=" + line.lineId + " cap=" + demand.cap
                   + " monthly_demand=" + demand.monthlyDemand
                   + " capacity_per_plane=" + demand.capacityPerPlane
                   + " routes_a=" + demand.routesA + " routes_b=" + demand.routesB
                   + " planes=" + have + " physical_cap=" + physicalMaxPlanes
                   + " applied_cap=" + maxPlanesForAirport);
      }
      if (have >= maxPlanesForAirport) { OpexAirFleetRefusal(line, year, "Q"); continue; }
    }
    if (("deadStreak" in line) && line.deadStreak >= 1) { OpexAirFleetRefusal(line, year, "S"); continue; }
    if (("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); continue; }

    /* fleet_fix : cette garde pricait le MEILLEUR avion du catalogue, alors qu'OpexAirAddPlane
     * clone le gabarit de LA LIGNE (builder_air.nut:224, prix lu sur l'engin du vehicule existant).
     * Une ligne a helices desservant un petit aeroport, face a un catalogue passe au gros jet,
     * voyait donc `need` plusieurs fois trop grand : `money < need` -> break, et une ligne
     * rentable ne grandissait jamais alors que la tresorerie etait la. La garde interne
     * d'OpexAirAddPlane etant correcte, celle-ci ne produisait que des FAUX NEGATIFS
     * (docs/taches.md S0 nonies). On price desormais l'avion qu'on va reellement acheter. */
    local planePrice = (this._catalog.plane != null) ? this._catalog.plane.price : 30000;
    if ((FLEET_FIX || AIR_FLEET_LINE_PRICE) && ("vehicles" in line)) {
      foreach (v in line.vehicles) {
        if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
        local ownPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
        if (ownPrice > 0) planePrice = ownPrice;
        break;
      }
    }
    /* Croissance d'une ligne aerienne EXISTANTE : aucun aeroport a batir, donc rien que
     * cette marge doive couvrir. 88 refus insufficient_cash pour 3 acceptations mesures
     * sur 3 parties x 2 ans (results/diag_1v1_decisions.json). */
    local need = planePrice + OpexCashReserve() + (AIR_MARGIN_V2 ? 0 : 2000);
    local addedThisPass = 0;
    // (d) au plus un avion par ligne et par an sous marginal_fleet=1 ; 4 (repli actuel) sous 0.
    local maxAddedPerPass = MARGINAL_FLEET ? 1 : 4;
    /* C14 : Dimensionnement dynamique de flotte par le stock au sol (AAAHogEx route.nut:2896-2921).
     * Si AIR_FLEET_BUFFER >= 0 : calcule buildNum = (maxWait - bottom) / capacity.
     * Si buildNum < 1 : refus W (pas assez de cargo au sol).
     * Sinon : autorise jusqu'a min(buildNum, 4) avions dans ce passage. */
    if (AIR_FLEET_BUFFER >= 0) {
      local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
      if (planeCap <= 0 && ("vehicles" in line)) {
        foreach (v in line.vehicles) {
          if (AIVehicle.IsValidVehicle(v)) {
            planeCap = AIVehicle.GetCapacity(v, line.cargo);
            if (planeCap > 0) { line.planeCapacity <- planeCap; break; }
          }
        }
      }
      local stA = AIStation.GetStationID(line.stationA);
      local hasB = ("stationB" in line) && line.stationB != null;
      local stB = hasB ? AIStation.GetStationID(line.stationB) : 0;
      local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
      local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
      local maxWait = (waitA > waitB) ? waitA : waitB;

      local bottom = (AIR_FLEET_BUFFER < planeCap) ? AIR_FLEET_BUFFER : planeCap;
      local buildNum = 0;
      if (maxWait > bottom && planeCap > 0) {
        buildNum = (maxWait - bottom) / planeCap;
      }
      if (buildNum < 1) {
        OpexAirFleetRefusal(line, year, "W");
        continue;
      }
      maxAddedPerPass = (buildNum < 4) ? buildNum : 4;
    }
    if (plan != null) {
      /* Mode a blanc : on ne touche ni a la tresorerie ni a la ligne. Le test de capital est celui
       * du portefeuille, pas celui d'ici -- c'est tout l'objet de l'arbitrage. */
      local room = maxPlanesForAirport - have;
      local want = (room < maxAddedPerPass) ? room : maxAddedPerPass;
      if (want > 0) plan.append({ line = line, want = want, planePrice = planePrice });
      continue;
    }
    while (have < maxPlanesForAirport && addedThisPass < maxAddedPerPass) {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) { OpexAirFleetRefusal(line, year, "M"); break; }
      local grown = OpexAirAddPlane(line);
      if (grown.added <= 0) { OpexAirFleetRefusal(line, year, "X"); break; }
      have += grown.added;
      addedThisPass += grown.added;
      line.vehCount <- have;
      line.trains = have;
    }
    if (addedThisPass > 0) {
      line.lastAirFleetYear <- year;
      line.lastAirFleetDate <- AIDate.GetCurrentDate();
      if (DECISION_LOG) {
        local yieldVal = OpexAirFleetYield(line);
        OpexDecide("AIR_FLEET", "action=grow line=" + line.lineId + " yield=" + yieldVal + " planes_before=" + (have - addedThisPass) + " planes_after=" + have + " added=" + addedThisPass);
      }
      AILog.Info("[AIR_FLEET] line=" + line.lineId + " added=" + addedThisPass + " total=" + have);
      OpexSign(AIMap.GetTileIndex(1, 10 + line.lineId), "FG|" + (year % 100) + "|" + line.lineId + "|" + have + "|K");
    }
  }
  return true;
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

function OpexAI::_triggerScrapLine(line, criterion)
{
  if (("scrapping" in line) && line.scrapping) return;
  line.scrapping = true;
  line.deadStreak = DEAD_STREAK_THRESHOLD;
  local anchor = AIMap.GetTileIndex(1, 1);
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local ids = [];
  local vehicleType = OpexLineVehicleType(line);
  /* Les lignes air gardent leurs IDs de flotte. Meme si l'aeroport A est invalide, les avions
   * doivent rejoindre un hangar et etre vendus ; une liste par gare serait alors vide et
   * retirerait seulement la ligne logique en laissant les couts d'exploitation actifs. */
  local stationA = AIStation.GetStationID(line.stationA);
  local vehicles = ("vehicles" in line) ? line.vehicles
      : (AIStation.IsValidStation(stationA) ? OpexLineVehicleIds(line, stationA) : []);
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
    AIVehicle.SendVehicleToDepot(v);
    ids.append(v);
    if (EVENT_DEPOT_SELL && this._vehiclesToScrap != null) {
      this._vehiclesToScrap.rawset(v, line.lineId);
    }
  }
  line.scrapVehicles = ids;
  if (DECISION_LOG) {
    local m = ("mode" in line) ? line.mode : "unknown";
    OpexDecide("SCRAP_LINE", "action=start line=" + line.lineId + " mode=" + m + " dead_streak=" + line.deadStreak + " threshold=" + DEAD_STREAK_THRESHOLD + " vehicles=" + ids.len() + " criterion=" + criterion);
  }
  local signCode = (criterion == "industry_close") ? "C" : "2";
  OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + signCode);
}

function OpexAI::_scrapDeadLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local toRemove = [];

  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("deadStreak" in line)) continue;

    if (!line.scrapping && line.deadStreak >= DEAD_STREAK_THRESHOLD) {
      this._triggerScrapLine(line, "dead_streak");
    }

    if (line.scrapping) {
      if (EVENT_DEPOT_SELL && this._vehiclesToScrap != null && ("scrapVehicles" in line)) {
        foreach (v in line.scrapVehicles) {
          if (AIVehicle.IsValidVehicle(v) && !(v in this._vehiclesToScrap)) {
            this._vehiclesToScrap.rawset(v, line.lineId);
          }
        }
      }
      local remaining = [];
      foreach (v in line.scrapVehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;  // deja vendu ou detruit
        if (AIVehicle.IsStoppedInDepot(v)) {
          AIVehicle.SellVehicle(v);
          if (this._vehiclesToScrap != null && (v in this._vehiclesToScrap)) {
            delete this._vehiclesToScrap[v];
          }
          if (DECISION_LOG) {
            OpexDecide("SCRAP_LINE", "action=sell_vehicle line=" + line.lineId + " vehicle=" + v);
          }
        } else {
          remaining.append(v);
        }
      }
      line.scrapVehicles = remaining;
      /* Sortie de secours du ferraillage. Sans elle, la SEULE sortie etait `remaining.len() == 0` :
       * un vehicule qui ne peut plus atteindre un depot -- depot detruit, route coupee, convoi
       * bloque -- figeait la ligne DEFINITIVEMENT. Elle restait alors dans _lines, re-scannee
       * chaque annee, payant son cout d'exploitation, et ses deux extremites continuaient de
       * bloquer _tooClose pour de nouveaux candidats : exactement l'interblocage que le retrait
       * est cense empecher (docs/taches.md S0 nonies).
       *
       * On borne donc la phase en ANNEES. Les vehicules encore vivants sont abandonnes en l'etat
       * plutot que de garder la ligne en vie : ils continueront a rouler, mais la ligne libere ses
       * origines et cesse d'etre re-scannee. Panneau DL|...|4 pour distinguer cette sortie de la
       * sortie propre DL|...|3. */
      if (!("scrapStartYear" in line)) line.scrapStartYear <- year;
      local stuck = (year - line.scrapStartYear) >= SCRAP_TIMEOUT_YEARS;
      if (remaining.len() == 0 || stuck) {
        if (this._vehiclesToScrap != null) {
          foreach (v in remaining) {
            if (v in this._vehiclesToScrap) delete this._vehiclesToScrap[v];
          }
        }
        toRemove.append(i);  // i = position physique dans _lines, pour le retrait -- pas le sign
        if (DECISION_LOG) {
          local crit = (remaining.len() == 0) ? "all_sold" : "timeout";
          OpexDecide("SCRAP_LINE", "action=removed line=" + line.lineId + " criterion=" + crit + " remaining=" + remaining.len());
        }
        OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + (remaining.len() == 0 ? "3" : "4"));
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
    if (("expandBlocked" in line) && line.expandBlocked) continue;
    if (("expandRetryCycle" in line) && line.expandRetryCycle > this._taskCycle) continue;
    if (!("depot" in line) || !AIRoad.IsRoadDepotTile(line.depot)) continue;
    if (("deadStreak" in line) && line.deadStreak > 0) continue;
    /* fleet_fix : `vehCount` n'est ecrit que par _reportLines, au plus UNE fois par an, et les
     * dicts de ligne routiere n'en portent pas a la construction. Or la file execute `projects`
     * puis `refleet` DANS LE MEME CYCLE : une ligne tout juste batie arrivait donc ici avec
     * have = 0 face a un target valant sa flotte reelle, et OpexRoadRefleet repartait -- en
     * sautant la reprise de gabarit faute de have > 0, donc en creant un vehicule avec sa PROPRE
     * liste d'ordres puis en clonant le reste. Toute ligne routiere neuve achetait ainsi une
     * seconde flotte complete (docs/taches.md S0 nonies, trouvaille 2). Le repli est desormais la
     * flotte reellement posee a la construction, pas zero. */
    local have = 0;
    if ("vehCount" in line) {
      have = line.vehCount;
    } else if ((FLEET_FIX || ROAD_FLEET_FIX) && ("trains" in line)) {
      have = line.trains;
    }
    local target = ("predTrains" in line) ? line.predTrains : (("trains" in line) ? line.trains : 1);
    if (("trains" in line) && line.trains > target) target = line.trains;
    if (target < 1) target = 1;

    // Dimensionnement dynamique intelligent basé sur les flux physiques
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local waitingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : 0;
    local waitingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
    local ratingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoRating(stationA, line.cargo) : 100;
    local ratingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoRating(stationB, line.cargo) : 100;
    local minRating = (ratingA < ratingB) ? ratingA : ratingB;
    local totalWaiting = waitingA + waitingB;

    // Analyse des véhicules de la ligne : y en a-t-il qui attendent à l'arrêt ?
    local vehicles = OpexLineVehicleIds(line, stationA);
    local isAnyWaiting = false;
    local movingCount = 0;
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.GetCurrentSpeed(v) == 0) {
        /* fleet_fix : « vitesse nulle » n'est PAS un embouteillage -- c'est l'etat NORMAL d'un
         * vehicule en cours de chargement a un arret, et les lignes de fret routier sont baties
         * avec OF_FULL_LOAD_ANY, donc un camion y passe la majeure partie de son cycle. Les trois
         * heuristiques de croissance plus bas exigeant toutes !isAnyWaiting, la situation qui
         * devrait declencher la croissance -- du cargo qui s'accumule pendant qu'un camion fait le
         * plein -- etait lue comme « deja sature, ne pas grandir ». Le signal etait donc inverse
         * par rapport a son intention (docs/taches.md S0 nonies, trouvaille 3). On ne compte
         * desormais comme bloque qu'un vehicule arrete EN LIGNE, pas a quai. */
        if ((!FLEET_FIX && !ROAD_LOADING_FIX) || AIVehicle.GetState(v) != AIVehicle.VS_AT_STATION) isAnyWaiting = true;
        else movingCount++;
      } else movingCount++;
    }

    if (("lastProfit" in line) && line.lastProfit < -200 && have >= 2) continue;
    /* marginal_fleet = 1 : le profit marginal attendu du vehicule supplementaire doit etre
     * positif -- pas de lastProfit connu et STRICTEMENT positif, pas de croissance au-dela de la
     * reconstitution du parc d'origine (missing/target calcules plus haut, jamais touches ici).
     * Sous 0 (defaut) ce garde-fou n'existe pas et les trois heuristiques ci-dessous restent
     * exactement ce qu'elles etaient. */
    if (MARGINAL_FLEET && (!("lastProfit" in line) || line.lastProfit <= 0)) continue;

    local capacity = ("capacity" in line && line.capacity > 0) ? line.capacity : 25;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local extraNeeded = 0;

    local physicalCap = OpexRoadPhysicalVehicleCap(
        ("nStopsA" in line) ? line.nStopsA : 1, ("nStopsB" in line) ? line.nStopsB : 1);

    // 1. S'il y a du stock en attente et que les véhicules circulent bien
    if (totalWaiting >= capacity && !isAnyWaiting) {
      extraNeeded = totalWaiting / capacity;
      if (extraNeeded > 3) extraNeeded = 3;
    }
    // 2. Si la note de station s'effondre faute de fréquence (distance longue)
    else if (minRating < 65 && have < physicalCap && !isAnyWaiting && money > 35000) {
      extraNeeded = 1;
    }
    // 3. Si la ligne est très rentable (> 1000 £) et qu'on a du cash
    else if (("lastProfit" in line) && line.lastProfit > 1000 && have < physicalCap && money > 60000 && !isAnyWaiting) {
      extraNeeded = 1;
    }

    /* Un véhicule supplémentaire ne peut ajouter de valeur que s'il trouve
     * un quai libre (docs/mecanique_jeu S11). Au-delà de physicalCap (2 par quai),
     * il bloque la voirie et détruit le profit par les coûts d'exploitation. */
    if (have + extraNeeded > physicalCap) extraNeeded = physicalCap - have;
    if (extraNeeded < 0) extraNeeded = 0;

    if (have + extraNeeded > target) target = have + extraNeeded;
    if (target > physicalCap) target = physicalCap;
    if (have >= target) continue;
    local refill = OpexRoadRefleet(this._catalog, line, have, target);
    if (refill.added > 0) {
      line.vehCount <- refill.after;
      if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
    }
    if (DECISION_LOG) {
      if (refill.added > 0) {
        OpexDecide("ROAD_REFLEET", "action=refill line=" + line.lineId + " added=" + refill.added + " total=" + refill.after);
      } else {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (!("lastRefleetRefuseMonth" in line) || line.lastRefleetRefuseMonth != ym) {
          line.lastRefleetRefuseMonth <- ym;
          OpexDecide("ROAD_REFLEET", "action=refuse line=" + line.lineId + " reason=" + refill.reason + " have=" + have + " target=" + target);
        }
      }
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

  local elapsedTicks = AIController.GetTick() - this._startTick;
  local totalAvail = elapsedTicks * OPS_PER_TICK;
  local totalUsed = this._budget.total();
  local totalUnused = totalAvail - totalUsed;
  if (totalUnused < 0) totalUnused = 0;
  local pctUsed = (totalAvail > 0) ? ((totalUsed * 1000) / totalAvail) : 0;
  local pctUnused = 1000 - pctUsed;
  local btText = "BT|" + (totalUsed / 1000000) + "M|" + (totalUnused / 1000000) + "M|" + pctUsed + "|" + pctUnused;
  if ("tot" in _budgetSignIds && AISign.IsValidSign(_budgetSignIds["tot"])) {
    AISign.SetName(_budgetSignIds["tot"], btText);
  } else {
    _budgetSignIds["tot"] <- AISign.BuildSign(AIMap.GetTileIndex(20, 1), btText);
  }

  local catY = 2;
  foreach (cat, spent in this._budget.totals) {
    local catPct = (totalUsed > 0) ? ((spent * 1000) / totalUsed) : 0;
    local availPct = (totalAvail > 0) ? ((spent * 1000) / totalAvail) : 0;
    local bcText = "BC|" + cat + "|" + (spent / 1000) + "k|" + catPct + "|" + availPct;
    if (bcText.len() > 31) bcText = bcText.slice(0, 31);
    if (cat in _budgetSignIds && AISign.IsValidSign(_budgetSignIds[cat])) {
      AISign.SetName(_budgetSignIds[cat], bcText);
    } else {
      _budgetSignIds[cat] <- AISign.BuildSign(AIMap.GetTileIndex(20, catY), bcText);
    }
    catY++;
  }

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

  if (EVENT_SUBSIDY_PROBE && this._subsidyStats != null) {
    OpexSign(anchor, "SR|" + (year % 100) + "|" + this._subsidyStats.offers
                     + "|" + this._subsidyStats.matchedPool
                     + "|" + this._subsidyStats.awardedSelf
                     + "|" + this._subsidyStats.awardedOther
                     + "|" + this._subsidyStats.expiredWithoutAward);
    if (DECISION_LOG) {
      OpexDecide("SUBSIDY_REPORT", "year=" + year + " offers=" + this._subsidyStats.offers + " matched=" + this._subsidyStats.matchedPool + " awarded_self=" + this._subsidyStats.awardedSelf + " awarded_other=" + this._subsidyStats.awardedOther + " expired=" + this._subsidyStats.expiredWithoutAward);
    }
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
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=reborrow drew=" + drew + " new_loan=" + newLoan + " covered=" + covered + " need=" + need + " cash_after=" + after);
  }
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
  OpexSign(AIMap.GetTileIndex(1, 1), "LF|" + (year % 100) + "|" + cash + "|" + loan);
  if (loan <= 0) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=none reason=no_loan cash=" + cash + " floor=" + LOAN_REPAY_FLOOR);
    }
    return;
  }

  if (cash <= LOAN_REPAY_FLOOR) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=refuse_repay reason=cash_below_floor cash=" + cash + " floor=" + LOAN_REPAY_FLOOR + " loan=" + loan);
    }
    return;
  }

  local interval = AICompany.GetLoanInterval();
  local minNewLoan = loan - (cash - LOAN_REPAY_FLOOR);
  if (minNewLoan < 0) minNewLoan = 0;
  local newLoan = ((minNewLoan + interval - 1) / interval) * interval;
  if (newLoan >= loan) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=refuse_repay reason=less_than_interval cash=" + cash + " floor=" + LOAN_REPAY_FLOOR + " loan=" + loan + " interval=" + interval);
    }
    return;  // moins d'un palier remboursable : pas la peine
  }

  local repaid = loan - newLoan;
  AICompany.SetLoanAmount(newLoan);
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "LR|" + year + "|" + repaid + "|" + newLoan);
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=repay repaid=" + repaid + " new_loan=" + newLoan + " cash=" + cash + " floor=" + LOAN_REPAY_FLOOR);
  }
}

function OpexAI::_findLineById(lineId)
{
  foreach (line in this._lines) {
    if (("lineId" in line) && line.lineId == lineId) return line;
  }
  return null;
}

/* Choisit au plus UNE expansion par an. L'infrastructure est deja payee et aucun pathfinder ne
 * tourne : le classement porte donc sur le gain annuel marginal, les candidats ayant tous le
 * meme ordre de grandeur d'opcodes. Le revenu a capacite pleine de N+1 wagons est recale par le
 * revenu REEL de N wagons ; ce ratio conserve la physique (traction, temps, capacite) sans croire
 * la demande pax surestimee du catalogue. */
function OpexAI::_expandRailLines(year)
{
  /* G6§1 : la garde d'entree coupait TOUT sur !RAIL_EXPAND, y compris le bloc RAIL_REFLEET
   * plus bas -- seul site d'appel de OpexBuildSecondTrain et OpexUpgradeRailLineToDoubleTrack.
   * Avec les defauts livres (rail_expand = 0, rail_refleet = 1) aucune ligne rail ne pouvait donc
   * JAMAIS gagner un second train ni une seconde voie. Desormais inconditionnel. */
  if ((!RAIL_EXPAND && !RAIL_REFLEET) || this._railExpansion != null) return;
  /* Une recherche A* en cours (ligne neuve ou upgrade) : ne pas en empiler une seconde. */
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null) return;
  this._budget.begin();
  local best = null;
  local nEligible = 0;
  local nSaturated = 0;
  local nPersistent = 0;
  local nPositive = 0;
  foreach (line in this._lines) {
    /* G6§1 : quand on n'est entre QUE pour le refleet (rail_expand = 0, rail_refleet = 1),
     * l'expansion de wagons ne doit pas s'exercer -- on ne fait que traverser vers le bloc
     * RAIL_REFLEET, `best` restant nul. */
    if (!RAIL_EXPAND) break;
    if ((("mode" in line) && line.mode != "rail") || !("wagons" in line) || !("platformLength" in line) ||
        !("loco" in line) || !("kind" in line)) continue;
    if (line.trains != 1 || !("vehCount" in line) || line.vehCount != 1) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("lastProfit" in line) || line.lastProfit <= 0 ||
        !("lastRevenue" in line) || line.lastRevenue <= 0) continue;
    if (!(line.cargo in this._catalog.wagonByCargo)) continue;
    if (line.wagons >= OpexRailNominalMaxWagons(line.platformLength)) continue;
    nEligible++;

    local oldEcon = OpexRailFixedConsist(this._catalog, line.cargo, line.distance,
                                         line.kind, line.loco, line.wagons);
    local newEcon = OpexRailFixedConsist(this._catalog, line.cargo, line.distance,
                                         line.kind, line.loco, line.wagons + 1);
    if (oldEcon == null || newEcon == null || oldEcon.capacityRevenueAnnual <= 0) continue;

    local wagon = this._catalog.wagonByCargo[line.cargo];
    local waitingA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
    local waitingB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
    local waiting = line.kind == "freight" ? waitingA : waitingA + waitingB;
    local backlogThreshold = line.kind == "freight" ? wagon.capacity : 2 * wagon.capacity;
    local utilPermille = (line.lastRevenue * 1000) / oldEcon.capacityRevenueAnnual;
    if (utilPermille > 1000) utilPermille = 1000;
    local saturated = waiting >= backlogThreshold || utilPermille >= RAIL_EXPAND_UTIL_PERMILLE;
    if (saturated) nSaturated++;
    local priorStreak = ("expandStreak" in line) ? line.expandStreak : 0;
    /* Un tour de file peut finir sans qu'une annee de jeu passe. Ne jamais compter deux fois le
     * meme GetProfitLastYear / backlog comme deux confirmations independantes. */
    if (!("lastExpandCheckYear" in line) || line.lastExpandCheckYear != year) {
      line.expandStreak <- saturated ? priorStreak + 1 : 0;
      line.lastExpandCheckYear <- year;
    }
    if (line.expandStreak < RAIL_EXPAND_STREAK) continue;
    nPersistent++;

    local capacityDelta = newEcon.capacityRevenueAnnual - oldEcon.capacityRevenueAnnual;
    if (capacityDelta <= 0) continue;
    local grossGain = (line.lastRevenue * capacityDelta) / oldEcon.capacityRevenueAnnual;
    local marginalProfit = grossGain - newEcon.wagonRunningAnnual - newEcon.wagonAmortAnnual;
    if (marginalProfit <= 0) continue;
    nPositive++;

    local vehicle = null;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsPrimaryVehicle(v) &&
          AIVehicle.GetVehicleType(v) == AIVehicle.VT_RAIL) { vehicle = v; break; }
    }
    if (vehicle == null) continue;
    if (best == null || marginalProfit > best.gain) {
      best = { line = line, vehicle = vehicle, wagon = wagon, oldEcon = oldEcon,
               newEcon = newEcon, gain = marginalProfit, waiting = waiting,
               util = utilPermille };
    }
  }
  local decisionOps = this._budget.end("expand_rail_decide");
  OpexSign(AIMap.GetTileIndex(1, 1), "EU|" + (year % 100) + "|" + nEligible + "|"
           + nSaturated + "|" + nPersistent + "|" + nPositive + "|" + decisionOps);
  if (best == null) {
    if (RAIL_REFLEET) {
      foreach (line in this._lines) {
        if ((("mode" in line) && line.mode != "rail") || !("wagons" in line) || !("loco" in line) || !("kind" in line)) continue;
        if (line.trains >= 2 || line.vehicles.len() >= 2) continue;
        if (("scrapping" in line) && line.scrapping) continue;
        if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
        if (!(line.cargo in this._catalog.wagonByCargo)) continue;

        local wagon = this._catalog.wagonByCargo[line.cargo];
        local waitingA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
        local waitingB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
        local waiting = line.kind == "freight" ? waitingA : waitingA + waitingB;
        local backlogThreshold = line.kind == "freight" ? (2 * wagon.capacity) : (4 * wagon.capacity);
        if (waiting < backlogThreshold) continue;

        // Cas 1 : Ligne deja doublee avec depot2 -> ajout immediat du 2e train
        if (("doubleTrack" in line) && line.doubleTrack == 1 && ("depot2" in line) && line.depot2 != null) {
          local trainCost = line.loco.price + line.wagons * wagon.price;
          local need = trainCost + OpexCashReserve();
          local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (money < need && REBORROW) money = OpexTryReborrow(need, money);
          if (money >= need) {
            local secondTrain = OpexBuildSecondTrain(this._catalog, line, OpexCashReserve());
            if (secondTrain.ok) {
              line.vehicles.append(secondTrain.train);
              line.trains = line.vehicles.len();
              line.vehCount <- line.vehicles.len();
              local anchor = AIMap.GetTileIndex(1, 1);
              OpexSign(anchor, "RD|" + (year % 100) + "|" + line.lineId + "|" + line.trains);
              if (DECISION_LOG) {
                OpexDecide("RAIL_EXPAND", "action=second_train line=" + line.lineId + " trains=" + line.trains);
              }
              return;
            }
          }
        }
        // Cas 2 : Ligne a voie unique -> doublement d'infrastructure et 2e train
        else if ((!("doubleTrack" in line) || line.doubleTrack == 0) &&
                 ("platformA" in line) && ("platformB" in line) &&
                 line.platformA != null && line.platformB != null) {
          local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
          local trackCost = line.distance * this._catalog.costTrackPerTile + 2 * line.platformLength * this._catalog.costStation + depotCost;
          local trainCost = line.loco.price + line.wagons * wagon.price;
          local need = trackCost + trainCost + OpexCashReserve();
          local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (money < need && REBORROW) money = OpexTryReborrow(need, money);
          if (money >= need) {
            if (RAIL_SEARCH_RESUMABLE) {
              local prep = OpexPrepareUpgradeSearch(line, HARD_ITERATION_CAP);
              local anchor = AIMap.GetTileIndex(1, 1);
              if (!prep.ok) {
                OpexSign(anchor, "RU|" + (year % 100) + "|" + line.lineId + "|" + prep.reason);
              } else {
                this._startRailUpgradeSearch(line, prep);
                return;
              }
            } else {
              local upgrade = OpexUpgradeRailLineToDoubleTrack(this._catalog, this._budget, line, OpexCashReserve(), HARD_ITERATION_CAP);
              local anchor = AIMap.GetTileIndex(1, 1);
              OpexSign(anchor, "RU|" + (year % 100) + "|" + line.lineId + "|" + upgrade.reason);
              if (DECISION_LOG) {
                OpexDecide("RAIL_EXPAND", "action=double_track line=" + line.lineId + " reason=" + upgrade.reason + " ok=" + (upgrade.ok ? 1 : 0));
              }
              if (upgrade.ok) {
                line.doubleTrack = 1;
                line.depot2 = upgrade.depot2;
                line.stationA2 = upgrade.stationA2;
                line.stationB2 = upgrade.stationB2;
                line.platformA2 = upgrade.platformA2;
                line.platformB2 = upgrade.platformB2;
                line.vehicles.append(upgrade.train);
                line.trains = line.vehicles.len();
                line.vehCount <- line.vehicles.len();
                return;
              }
            }
          }
        }
      }
    }
    return;
  }

  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = best.wagon.price + OpexCashReserve();
  if (money < need) {
    if (REBORROW) money = OpexTryReborrow(need, money);
    if (money < need) return;
  }

  local waitDays = (2 * best.oldEcon.oneWayDays).tointeger() + 60;
  if (waitDays < 120) waitDays = 120;
  if (waitDays > 730) waitDays = 730;
  this._railExpansion = {
    lineId = best.line.lineId, vehicle = best.vehicle, wagonId = best.wagon.id,
    oldWagons = best.line.wagons, newWagons = best.line.wagons + 1,
    newSpeed = best.newEcon.effectiveSpeed, newOneWayDays = best.newEcon.oneWayDays,
    gain = best.gain, waiting = best.waiting, util = best.util,
    decisionDate = AIDate.GetCurrentDate(), waitDays = waitDays,
    startDate = AIDate.GetCurrentDate(), phase = "approach", dispatchAttempts = 0,
    temporaryOrder = false, temporaryOrderPosition = -1,
    /* EU porte le cout de selection ; EX ne porte que dispatch + polls + construction, afin
     * que leur somme soit le debit total sans double comptage. */
    ops = 0, cost = 0,
  };
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "EG|" + (year % 100) + "|" + best.line.lineId + "|"
                   + best.line.wagons + "|" + (best.line.wagons + 1) + "|" + best.gain);
  OpexSign(anchor, "ES|" + (year % 100) + "|" + best.line.lineId + "|"
                   + best.waiting + "|" + best.util + "|" + best.line.expandStreak);
  if (DECISION_LOG) {
    OpexDecide("RAIL_EXPAND", "action=wagon_expansion line=" + best.line.lineId + " old_wagons=" + best.line.wagons + " new_wagons=" + (best.line.wagons + 1) + " gain=" + best.gain + " waiting=" + best.waiting + " util=" + best.util);
  }
  /* Si le train passe deja pres du depot, l'interception peut commencer dans ce meme tour. */
  if (AIVehicle.IsStoppedInDepot(best.vehicle) ||
      AIMap.DistanceManhattan(AIVehicle.GetLocation(best.vehicle), best.line.depot)
          <= RAIL_EXPAND_APPROACH_TILES) this._continueRailExpansion();
}

/* Avance la transaction sans attente bloquante. Tant que la rame est loin du depot, elle garde
 * ses ordres et son revenu normaux ; l'ordre d'arret temporaire n'est injecte qu'a l'approche. */
function OpexAI::_continueRailExpansion()
{
  if (this._railExpansion == null) return false;
  local state = this._railExpansion;
  local line = this._findLineById(state.lineId);
  local anchor = AIMap.GetTileIndex(1, 1);
  local year = AIDate.GetYear(AIDate.GetCurrentDate()) % 100;
  this._budget.begin();

  if (line == null || !AIVehicle.IsValidVehicle(state.vehicle)) {
    state.ops += this._budget.end("expand_rail_build");
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|V|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  if (state.phase == "resume") {
    local resumed = AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    if (resumed) {
      OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|K|" + state.ops + "|" + state.cost);
      this._railExpansion = null;
    }
    return true;
  }

  if (state.phase == "approach") {
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) {
      state.phase = "depot";
    } else {
      if (AIDate.GetCurrentDate() - state.decisionDate > state.waitDays) {
        state.ops += this._budget.end("expand_rail_dispatch");
        line.expandStreak <- 0;
        line.expandRetryCycle <- this._taskCycle + 3;
        OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|W|" + state.ops + "|0");
        this._railExpansion = null;
        return true;
      }
      if (!("depot" in line) || !AIRail.IsRailDepotTile(line.depot) ||
          AIMap.DistanceManhattan(AIVehicle.GetLocation(state.vehicle), line.depot)
              > RAIL_EXPAND_APPROACH_TILES) {
        state.ops += this._budget.end("expand_rail_dispatch");
        return true;
      }

      local dispatched = false;
      local position = AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT);
      if (position != AIOrder.ORDER_INVALID &&
          AIOrder.InsertOrder(state.vehicle, position, line.depot, AIOrder.OF_STOP_IN_DEPOT)) {
        if (AIOrder.SkipToOrder(state.vehicle, position)) {
          dispatched = true;
          state.temporaryOrder = true;
          state.temporaryOrderPosition = position;
        } else {
          AIOrder.RemoveOrder(state.vehicle, position);
        }
      }
      if (!dispatched) dispatched = AIVehicle.SendVehicleToDepot(state.vehicle);
      state.dispatchAttempts++;
      state.ops += this._budget.end("expand_rail_dispatch");
      if (!dispatched) {
        if (state.dispatchAttempts >= 3) {
          line.expandRetryCycle <- this._taskCycle + 3;
          OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|G|" + state.ops
                           + "|" + AIError.GetLastError());
          this._railExpansion = null;
        }
        return true;
      }
      state.phase = "depot";
      state.startDate = AIDate.GetCurrentDate();
      return true;
    }
  }

  if (!AIVehicle.IsStoppedInDepot(state.vehicle)) {
    if (AIDate.GetCurrentDate() - state.startDate > RAIL_EXPAND_TIMEOUT_DAYS) {
      if (state.temporaryOrder &&
          AIOrder.IsValidVehicleOrder(state.vehicle, state.temporaryOrderPosition)) {
        AIOrder.RemoveOrder(state.vehicle, state.temporaryOrderPosition);
      } else {
        /* Deuxieme appel = annulation documentee de l'ordre depot automatique. */
        AIVehicle.SendVehicleToDepot(state.vehicle);
      }
      state.ops += this._budget.end("expand_rail_build");
      line.expandStreak <- 0;
      line.expandRetryCycle <- this._taskCycle + 3;
      OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|T|" + state.ops + "|0");
      this._railExpansion = null;
      return true;
    }
    state.ops += this._budget.end("expand_rail_build");
    return true;
  }

  if (state.temporaryOrder) {
    if (AIOrder.IsValidVehicleOrder(state.vehicle, state.temporaryOrderPosition) &&
        AIOrder.IsGotoDepotOrder(state.vehicle, state.temporaryOrderPosition)) {
      if (!AIOrder.RemoveOrder(state.vehicle, state.temporaryOrderPosition)) {
        /* Ne jamais abandonner un train arrete avec notre ordre temporaire encore attache. */
        state.ops += this._budget.end("expand_rail_build");
        return true;
      }
    }
    state.temporaryOrder = false;
  }

  local depot = AIVehicle.GetLocation(state.vehicle);
  if (!AIRail.IsRailDepotTile(depot)) {
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|D|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }
  local wagonPrice = AIEngine.GetPrice(state.wagonId);
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < wagonPrice + OpexCashReserve()) {
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|C|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  local cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local car = AIVehicle.BuildVehicle(depot, state.wagonId);
  if (!AIVehicle.IsValidVehicle(car)) {
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|B|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  if (AIVehicle.GetLength(state.vehicle) + AIVehicle.GetLength(car) > line.platformLength * 16) {
    AIVehicle.SellVehicle(car);
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandBlocked <- true;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|L|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }
  if (!AIVehicle.MoveWagon(car, 0, state.vehicle, 0)) {
    if (AIVehicle.IsValidVehicle(car)) AIVehicle.SellVehicle(car);
    AIVehicle.StartStopVehicle(state.vehicle);
    state.ops += this._budget.end("expand_rail_build");
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|M|" + state.ops + "|0");
    this._railExpansion = null;
    return true;
  }

  state.cost = cashBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  line.wagons = state.newWagons;
  line.wagonId <- state.wagonId;
  line.effectiveSpeed = state.newSpeed;
  line.predOneWayDays = state.newOneWayDays;
  line.headwayDays = 2 * state.newOneWayDays;
  line.expandStreak <- 0;
  local expansionCount = ("railExpansions" in line) ? line.railExpansions : 0;
  line.railExpansions <- expansionCount + 1;
  line.lastExpansionYear <- AIDate.GetYear(AIDate.GetCurrentDate());
  state.phase = "resume";
  local resumed = AIVehicle.StartStopVehicle(state.vehicle);
  state.ops += this._budget.end("expand_rail_build");
  if (resumed) {
    OpexSign(anchor, "EX|" + year + "|" + state.lineId + "|K|" + state.ops + "|" + state.cost);
    this._railExpansion = null;
  }
  return true;
}

/* Demarre une recherche A* ferroviaire reprenable. Premiere tranche dans ce tour ; si elle
 * ne suffit pas, l'etat vit dans this._railSearch et _continueRailSearch reprend au suivant.
 * Fonction de classe, pas une closure : Squirrel ne capture jamais les locales englobantes. */
function OpexAI::_startRailSearch(candidate, join, placeJoin, alternativeRatio, hardCap, posPacked)
{
  local plan = OpexPrepareRailRoute(this._catalog, this._budget, candidate, alternativeRatio,
                                    join, hardCap);
  if (plan.plansA == null) return { pending = false, plan = plan };
  local pathfinder = null;
  local segmented = null;
  if (RAIL_SEGMENTED_SEARCH) {
    segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, plan.iterationBudget, null);
    if (segmented == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + plan.iterationBudget);
      plan.reason = "NOPA";
      return { pending = false, plan = plan };
    }
  } else {
    pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, null);
    if (pathfinder == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + plan.iterationBudget);
      plan.reason = "NOPA";
      return { pending = false, plan = plan };
    }
  }
  this._railSearch = {
    kind = "primary",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = plan.iterationBudget,
    /* Borne horaire large : le budget d'iterations est la vraie limite (piege 1). */
    safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
    plan = plan,
    candidate = candidate,
    join = join,
    placeJoin = placeJoin,
    alternativeRatio = alternativeRatio,
    hardCap = hardCap,
    posPacked = posPacked,
  };
  this._continueRailSearch();
  if (this._railSearch == null) {
    return { pending = false, plan = (("railPlan" in candidate) ? candidate.railPlan : plan) };
  }
  if (this._railSearch.phase == "build") {
    local completed = candidate.railPlan;
    this._railSearch = null;
    return { pending = false, plan = completed };
  }
  return { pending = true, plan = null };
}

/* Avance d'une tranche, ou consomme un plan/upgrade pret. Appele en TETE de _runNextTask. */
function OpexAI::_continueRailSearch()
{
  if (this._railSearch == null) return;
  local state = this._railSearch;
  if (state.phase == "build") {
    if (state.kind == "upgrade") this._consumeRailUpgrade();
    return;
  }
  if (state.phase != "search") return;

  this._budget.begin();
  local deadlineTick = state.safetyDeadline;
  if (RAIL_MICRO_DEADLINE) {
    /* C20 : echeance locale par micro-etape. 50 iters prennent ~17 ticks ; BUILD_TICK_MARGIN (3000)
     * laisse une large marge de securite contre un blocage dans la tranche sans jamais
     * imputer le temps des autres taches de la file (docs/cible.md §2.1). */
    deadlineTick = AIController.GetTick() + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;
  }
  local slice;
  if (("segmented" in state) && state.segmented != null) {
    slice = OpexAdvanceSegmentedSearch(state.segmented, RAIL_SEARCH_SLICE, deadlineTick);
  } else {
    slice = OpexAdvanceRailPathfinder(state.pathfinder, state.spent, state.iterationBudget,
                                      deadlineTick, RAIL_SEARCH_SLICE);
  }
  /* spent est le CUMUL de toutes les tranches : c'est le denominateur du classement. */
  state.spent = slice.iterations;
  if (state.kind == "primary") {
    state.plan.opcodes += this._budget.end("build_search");
    state.plan.iterations = state.spent;
  } else {
    this._budget.end("build_search");
  }
  if (!slice.done) {
    /* C41.48 : sonde passive a chaque frontiere de tranche (slice.stop == "CONT" ici, la SEULE
     * valeur qui rend done=false -- OpexSegmentedResult, builder_rail.nut). Rien n'est coupe :
     * mesure si un test de domination (C41.49) aurait seulement l'occasion de se declencher.
     * kind == "primary" seulement : une recherche d'upgrade n'a ni candidate ni profit/capital
     * au meme sens (state.line, pas state.candidate). */
    if (C41_RAIL_DOMINATION_PROBE && state.kind == "primary"
        && ("segmented" in state) && state.segmented != null) {
      local seg = state.segmented;
      local prefixLen = (seg.prefix != null) ? seg.prefix.len() : 0;
      local distRemaining = -1;
      if (prefixLen > 0) {
        distRemaining = AIMap.DistanceManhattan(seg.prefix[prefixLen - 1], seg.destinationCenter);
      }
      /* Le meilleur projet FINANCABLE, pas seulement le mieux classe : rang 0 peut deja etre
       * le candidat rail en cours de recherche (capital estime, pas encore construit) ou un
       * projet hors de portee de la caisse -- OpexAvailableCapital() est la meme formule
       * centralisee que _consumeRailSearch/_tryBuildProjects utilisent pour decider. */
      local bestRank = -1;
      local bestMode = "none";
      local bestScore = 0;
      local bestCost = 0;
      if (this._projects != null && this._projects.best != null) {
        local available = OpexAvailableCapital();
        for (local i = 0; i < this._projects.best.len(); i++) {
          local p = this._projects.best[i];
          if (p == null || p.capital > available) continue;
          bestRank = i;
          bestMode = p.mode;
          bestScore = ((TENSION_SCORING || SHADOW_PRICING) && ("tensionScore" in p)) ? p.tensionScore : p.budgetScore;
          bestCost = p.capital;
          break;
        }
      }
      OpexC41RailDominationLog("src=" + state.candidate.src + " dst=" + state.candidate.dst
          + " spent=" + state.spent + " remaining=" + (state.iterationBudget - state.spent)
          + " segments=" + slice.segments + " backtracks=" + slice.backtracks
          + " prefix_len=" + prefixLen + " dist_remaining=" + distRemaining
          + " rail_profit=" + state.candidate.profitAnnual + " rail_capital=" + state.candidate.capital
          + " best_rank=" + bestRank + " best_mode=" + bestMode + " best_score=" + bestScore
          + " best_cost=" + bestCost);
    }
    return;
  }

  if (DECISION_LOG) {
    OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " iters=" + state.spent + " budget=" + state.iterationBudget);
  }

  if (state.kind == "primary") {
    local plan = OpexCompleteRailRouteAfterSearch(this._catalog, state.candidate, state.plan,
                                                  slice, state.join);
    state.candidate.railPlan <- plan;
    state.pathfinder = null;
    state.phase = "build";
    return;
  }
  if (state.kind == "upgrade") {
    /* `search` n'existe pas dans l'etat initial : en Squirrel, une nouvelle
     * cle de table exige `<-`, sinon le premier upgrade leve une exception. */
    state.search <- slice;
    state.pathfinder = null;
    state.phase = "build";
    return;
  }
}

/* Consomme le railPlan produit par la recherche reprenable. "cash" = on garde l'etat pour
 * reessayer quand la caisse le permet (c'est exactement l'argent qui montait a vide pendant
 * le gel de 7 mois). */
function OpexAI::_consumeRailSearch(year)
{
  local state = this._railSearch;
  local candidate = state.candidate;
  local join = state.join;
  /* G3§1 : Un plan en echec (ABND/NOPA/DEAD) n'a besoin d'aucune tresorerie : OpexBuildLine
   * retourne immediatement sans construction. Le test de cash ne doit pas bloquer un plan
   * invalide en phase build indefiniment, sinon _railSearch ne se libere jamais et le
   * pipeline rail est neutralise (l'echec n'est pas non plus transmis a C22). */
  local planFailed = ("railPlan" in candidate) && candidate.railPlan != null
                     && !candidate.railPlan.ok;
  if (!planFailed) {
    local need = candidate.capital + OpexCashReserve();
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need && REBORROW) money = OpexTryReborrow(need, money);
    if (money < need) {
      /* C41.47 : pendant de la garde G3S1 ci-dessus, applique au motif tresorerie -- des le
       * premier blocage constate, liberer _railSearch pour que _expandRailLines et les AUTRES
       * candidats rail du portefeuille ne soient plus geles (main.nut:4445, 2574). candidate.
       * railPlan n'est PAS efface : OpexBuildLine le reutilise deja sans replanification quand
       * la carte n'a pas change (main G3S2), donc rien a revalider en plus du chemin existant. */
      if (C41_RAIL_CASH_RELEASE) {
        this._railSearch = null;
        OpexC41RailCashReleaseLog("reason=precheck src=" + candidate.src + " dst=" + candidate.dst
                                  + " need=" + need + " money=" + money);
      }
      return "cash";
    }
  }

  local result = OpexBuildLine(this._catalog, this._budget, candidate, state.alternativeRatio,
                               join, OpexCashReserve(), state.hardCap);
  /* Ne pas jeter le plan sur CASH : on reessaiera au prochain tour, sans refaire l'A*. */
  if (result.reason == "CASH") {
    if (C41_RAIL_CASH_RELEASE) {
      this._railSearch = null;
      OpexC41RailCashReleaseLog("reason=build_cash src=" + candidate.src + " dst=" + candidate.dst
                                + " capital=" + candidate.capital);
    }
    return "cash";
  }
  candidate.railPlan = null;
  local built = this._recordRailAttempt(candidate, result, join, state.placeJoin,
                                        state.posPacked, year);
  return built ? "built" : "failed";
}

/* Panneaux + enregistrement d'une tentative rail, reussie ou non. Facteur commun au chemin
 * bloquant et au chemin reprenable, pour que le denominateur (result.iterations) et les
 * panneaux OR/OB restent identiques. */
function OpexAI::_recordRailAttempt(candidate, result, join, placeJoin, posPacked, year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  local budgetInfo = (("budgetInfo" in result) && result.budgetInfo != null)
      ? result.budgetInfo : { path = "Z" };
  local iterationBudget = ("iterationBudget" in result) ? result.iterationBudget : 0;
  OpexSign(anchor, "OR|" + yy + "|" + this._nextLineId + "|" + posPacked
                           + "|" + budgetInfo.path + "S"
                           + OpexAttemptReasonCode(result.reason) + "|" + iterationBudget
                           + "|" + result.iterations);
  /* Bras experimental seulement. Sous 31 caracteres : SG|yy|lineId|seg|bt|loc. */
  if (RAIL_SEGMENTED_SEARCH) {
    local segs = ("segmentedSegments" in result) ? result.segmentedSegments : 0;
    local backs = ("segmentedBacktracks" in result) ? result.segmentedBacktracks : 0;
    local locs = ("segmentedLocalChoices" in result) ? result.segmentedLocalChoices : 0;
    OpexSign(anchor, "SG|" + yy + "|" + this._nextLineId + "|" + segs + "|" + backs + "|" + locs);
  }
  OpexSign(anchor, "OB|A|" + yy + "|" + this._nextLineId + "|" + posPacked
                           + "|" + result.opcodes + "|" + candidate.distance);
  if (result.reason == "SITEA" || result.reason == "SITEB" || result.reason == "SITEAB") {
    OpexSign(anchor, "PS|" + yy + "|" + this._nextLineId + "|" + posPacked
                            + "|" + result.siteClear + "|" + result.siteCargo + "|"
                            + result.siteCmd + "|" + result.siteKind + "|"
                            + result.joinEnd);
  }
  if (result.error != 0) OpexSign(anchor, "OV|" + this._nextLineId + "|" + result.error);

  if (DECISION_LOG) {
    if (result.ok) {
      local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
      OpexDecide("RAIL_BUILD", "line=" + this._nextLineId + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " cost=" + result.actualCost + " trains=" + result.trains + " wagons=" + result.wagons);
    } else {
      OpexDecide("RAIL_BUILD_FAIL", "line=" + this._nextLineId + " reason=" + result.reason + " error=" + result.error + " iters=" + result.iterations + " budget=" + iterationBudget);
    }
  }

  if (result.ok) {
    local idx = this._nextLineId;
    local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
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
    OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays.tointeger() + "|" + candidate.distance
                            + "|" + candidate.platformLength + "|" + candidate.effectiveSpeed.tointeger());
    OpexSign(anchor, "OL|" + idx + "|" + candidate.loco.id + "|" + candidate.loco.speed
                            + "|" + candidate.effectiveSpeed.tointeger() + "|" + candidate.loco.power
                            + "|" + candidate.loco.tractiveEffort);
    OpexSign(anchor, "PL|" + idx + "|" + result.platformLength + "|" + result.wagons
                            + "|" + result.trainLength + "|" + result.locoLength
                            + "|" + result.wagonLength);
    OpexSign(anchor, "PD|" + idx + "|" + result.wantedPlatformLength + "|"
                            + result.platformLength + "|" + result.plansA + "|"
                            + result.plansB + "|" + result.slopeRelaxed);
    OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                             + "|" + candidate.monthly);
    OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
    if (RAIL_COST_PROBE) {
      OpexSign(anchor, "DC|" + idx + "|" + result.capital + "|" + result.actualCost + "|"
                             + candidate.trains + "|" + result.trains + "|"
                             + result.doubleTrack);
    }
    if (STATION_JOIN || JOIN_PLACE) {
      local joinHow = "";
      if (placeJoin != null) joinHow = "|P";
      else if (join != null) joinHow = "|T";
      OpexSign(anchor, "PJ|" + idx + "|" + (join == null ? "N" : join.candidateEnd)
                               + "|" + (candidate.originServed ? 1 : 0) + joinHow);
    }
    if (isPaxNear) OpexSign(anchor, "PY|" + idx);

    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = candidate.profitAnnual, iterations = result.iterations,
      trains = result.trains, distance = candidate.distance, year = year,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      wagons = candidate.wagons, platformLength = result.platformLength,
      monthly = candidate.monthly, wagonId = this._catalog.wagonByCargo[candidate.cargo].id,
      loco = candidate.loco, effectiveSpeed = candidate.effectiveSpeed,
      headwayDays = candidate.headwayDays, stationRating = candidate.stationRating,
      vehicles = result.vehicles, platformA = result.platformA, platformB = result.platformB,
      depot = result.depot,
      doubleTrack = ("doubleTrack" in result) ? result.doubleTrack : 0,
      depot2 = ("depot2" in result) ? result.depot2 : null,
      stationA2 = ("stationA2" in result) ? result.stationA2 : null,
      stationB2 = ("stationB2" in result) ? result.stationB2 : null,
      platformA2 = ("platformA2" in result) ? result.platformA2 : null,
      platformB2 = ("platformB2" in result) ? result.platformB2 : null,
      mode = "rail", kind = candidate.kind,
      srcIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.src) : -1,
      dstIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.dst) : -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.trains, suspectedCrashes = 0,
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = idx,
    });
    this._nextLineId++;
    return true;
  }
  if (RAIL_COST_PROBE && ("actualCost" in result) && result.actualCost != 0) {
    OpexSign(anchor, "DC|" + this._nextLineId + "|" + result.capital + "|" + result.actualCost + "|"
                           + candidate.trains + "|0|0");
  }
  if (ABANDON_MEMORY && (result.reason == "ABND" || result.reason == "SITEA" || result.reason == "SITEB" ||
                         result.reason == "SITEAB" || result.reason == "NOPA" || result.reason == "STNFAIL")) {
    this._markPairAbandoned(OpexAbandonedPairKey(candidate));
  }
  return false;
}

function OpexAI::_startRailUpgradeSearch(line, prep)
{
  local pathfinder = null;
  local segmented = null;
  if (RAIL_SEGMENTED_SEARCH) {
    segmented = OpexCreateSegmentedSearch(prep.dualA, prep.dualB, prep.iterationBudget, prep.ignored);
    if (segmented == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + prep.iterationBudget);
      OpexSign(AIMap.GetTileIndex(1, 1), "RU|" + (AIDate.GetYear(AIDate.GetCurrentDate()) % 100)
               + "|" + line.lineId + "|NOPATH");
      return;
    }
  } else {
    pathfinder = OpexCreateRailPathfinder(prep.dualA, prep.dualB, prep.ignored);
    if (pathfinder == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=resumable outcome=NOPA iters=0 budget=" + prep.iterationBudget);
      OpexSign(AIMap.GetTileIndex(1, 1), "RU|" + (AIDate.GetYear(AIDate.GetCurrentDate()) % 100)
               + "|" + line.lineId + "|NOPATH");
      return;
    }
  }
  this._railSearch = {
    kind = "upgrade",
    phase = "search",
    pathfinder = pathfinder,
    segmented = segmented,
    spent = 0,
    iterationBudget = prep.iterationBudget,
    safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
    line = line,
    prep = prep,
  };
  this._continueRailSearch();
}

function OpexAI::_consumeRailUpgrade()
{
  local state = this._railSearch;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local upgrade = OpexExecuteUpgradeAfterSearch(this._catalog, this._budget, state.line,
                                                OpexCashReserve(), state.search, state.prep);
  /* Garder le trace si la caisse ne suffit plus : les autres taches tournent pendant ce temps. */
  if (upgrade.reason == "CASH") return;
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "RU|" + (year % 100) + "|" + state.line.lineId + "|" + upgrade.reason);
  if (DECISION_LOG) {
    OpexDecide("RAIL_EXPAND", "action=double_track line=" + state.line.lineId + " reason=" + upgrade.reason + " ok=" + (upgrade.ok ? 1 : 0));
  }
  if (upgrade.ok) {
    local line = state.line;
    line.doubleTrack = 1;
    line.depot2 = upgrade.depot2;
    line.stationA2 = upgrade.stationA2;
    line.stationB2 = upgrade.stationB2;
    line.platformA2 = upgrade.platformA2;
    line.platformB2 = upgrade.platformB2;
    line.vehicles.append(upgrade.train);
    line.trains = line.vehicles.len();
    line.vehCount <- line.vehicles.len();
  }
  this._railSearch = null;
}

/* C39.0 : note une invalidation sans la consommer. Les listes sont volontairement passees par
 * valeur, ce qui garde l'etat serialisable et le routeur sans dependance aux objets de plan.
 * Cette tranche ne change AUCUN dueCycle, ni `_portfolioInvalidated`, ni un candidat. */
function OpexAI::_markDirty(reason, catalogLayers = null, candidateLayers = null,
                            portfolio = false, selection = false, affectedKind = null,
                            affectedId = -1, affectedMode = null, targetedRelevant = true)
{
  if (!C39_INVALIDATION_PROBE || this._staleness == null) return;
  local revisionBumped = false;
  if (C39_DECISION_DELTA_PROBE && !this._staleness.topBeforeCaptured) {
    this._staleness.topBefore = OpexC39ProjectSignature(this._projects);
    this._staleness.topBeforeCaptured = true;
  }
  if (catalogLayers != null) {
    foreach (layer in catalogLayers) {
      if (layer in this._staleness.catalog) {
        if (C41_REVISION_PROBE && targetedRelevant && !this._staleness.catalog[layer]) {
          this._staleness.revisions.catalog[layer]++;
          this._staleness.dirtySince.catalog[layer] = AIDate.GetCurrentDate();
          if (layer == "water") {
            this._staleness.waterCatalogDirtyDate = AIDate.GetCurrentDate();
            this._staleness.waterCatalogDirtyTick = AIController.GetTick();
          }
          revisionBumped = true;
        }
        this._staleness.catalog[layer] = true;
      }
    }
  }
  if (candidateLayers != null) {
    foreach (layer in candidateLayers) {
      if (layer in this._staleness.candidates) {
        if (C41_REVISION_PROBE && targetedRelevant && !this._staleness.candidates[layer]) {
          this._staleness.revisions.candidates[layer]++;
          this._staleness.dirtySince.candidates[layer] = AIDate.GetCurrentDate();
          revisionBumped = true;
        }
        this._staleness.candidates[layer] = true;
      }
    }
  }
  if (portfolio) {
    if (C41_REVISION_PROBE && targetedRelevant && !this._staleness.portfolio) {
      this._staleness.revisions.portfolio++;
      this._staleness.dirtySince.portfolio = AIDate.GetCurrentDate();
      revisionBumped = true;
    }
    this._staleness.portfolio = true;
  }
  if (selection) {
    if (C41_REVISION_PROBE && targetedRelevant && !this._staleness.selection) {
      this._staleness.revisions.selection++;
      this._staleness.dirtySince.selection = AIDate.GetCurrentDate();
      revisionBumped = true;
    }
    this._staleness.selection = true;
  }
  this._staleness.events++;
  if (reason in this._staleness.reasons) this._staleness.reasons[reason]++;
  else this._staleness.reasons.rawset(reason, 1);
  if (affectedId >= 0) {
    if (affectedKind == "town") this._staleness.towns.rawset("" + affectedId, true);
    else if (affectedKind == "industry") this._staleness.industries.rawset("" + affectedId, true);
    else if (affectedKind == "engine") {
      this._staleness.engines.rawset("" + affectedId, true);
      if (affectedMode != null) this._staleness.engineModes.rawset("" + affectedId, affectedMode);
    }
  }
  OpexC39Log("C39_DIRTY", "reason=" + reason + " catalog=" + (catalogLayers != null ? catalogLayers.len() : 0)
             + " candidates=" + (candidateLayers != null ? candidateLayers.len() : 0)
             + " portfolio=" + (portfolio ? 1 : 0) + " selection=" + (selection ? 1 : 0)
             + " id=" + affectedId);
  if (C41_REVISION_PROBE && revisionBumped) {
    OpexC39Log("C41_REVISION", OpexC41RevisionSnapshot(this._staleness.revisions));
  }
  /* C41.1 : le routeur ne fait aucun rafraichissement. Il arme seulement la micro-tache eau ;
   * `catalog.water` reste son unique dependance et son unique acquittement futur. */
  if (C41_WATER_REFRESH && targetedRelevant && catalogLayers != null) {
    local waterDirty = false;
    foreach (layer in catalogLayers) if (layer == "water") waterDirty = true;
    if (waterDirty && this._taskQueue != null) {
      foreach (task in this._taskQueue) {
        if (task.name == "c41_water") {
          task.enabled = true;
          task.dueCycle = this._taskCycle;
          break;
        }
      }
    }
  }
  /* C41.15 : `catalog.road` n'est sali par C39 que pour EngineAvailable route. Le routeur reste
   * generique, mais cette garde rend la tache inerte pour toute future invalidation plus large. */
  if (C41_ROAD_REFRESH && targetedRelevant && catalogLayers != null) {
    local roadDirty = false;
    foreach (layer in catalogLayers) if (layer == "road") roadDirty = true;
    if (roadDirty && this._taskQueue != null) {
      foreach (task in this._taskQueue) {
        if (task.name == "c41_road") {
          task.enabled = true;
          task.dueCycle = this._taskCycle;
          break;
        }
      }
    }
  }
}

/* C39.0 : photographie coalescée juste avant de jeter l'etat, apres la regeneration mensuelle
 * historique. La signature du premier projet ne sert pas encore a DECIDER : elle donne au
 * diagnostic le resultat auquel les futures invalidations devront etre comparees. */
function OpexAI::_logStalenessRefresh(reason)
{
  if (!C39_INVALIDATION_PROBE || this._staleness == null) return;
  local cat = "";
  foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
    if (!this._staleness.catalog[layer]) continue;
    /* `slice`/`substr` differs between Squirrel builds; names explicites gardent la sonde
     * compatible avec l'API embarquee d'OpenTTD. */
    if (layer == "cargos") cat += "c";
    else if (layer == "towns") cat += "t";
    else if (layer == "industries") cat += "i";
    else if (layer == "rail") cat += "r";
    else if (layer == "road") cat += "d";
    else if (layer == "air") cat += "a";
    else if (layer == "water") cat += "w";
  }
  if (cat == "") cat = "-";
  local cand = "";
  foreach (layer in ["rail", "road", "air", "water"]) {
    if (!this._staleness.candidates[layer]) continue;
    if (layer == "rail") cand += "r";
    else if (layer == "road") cand += "d";
    else if (layer == "air") cand += "a";
    else if (layer == "water") cand += "w";
  }
  if (cand == "") cand = "-";
  local towns = 0;
  foreach (key, value in this._staleness.towns) towns++;
  local industries = 0;
  foreach (key, value in this._staleness.industries) industries++;
  local engines = 0;
  foreach (key, value in this._staleness.engines) engines++;
  local top = OpexC39ProjectSignature(this._projects);
  local topBefore = this._staleness.topBeforeCaptured ? this._staleness.topBefore : top;
  local topChanged = topBefore != top;
  local waterAgeDays = this._staleness.waterCatalogDirtyDate >= 0
      ? AIDate.GetCurrentDate() - this._staleness.waterCatalogDirtyDate : -1;
  OpexC39Log("C39_REFRESH", "reason=" + reason + " events=" + this._staleness.events
             + " cat=" + cat + " cand=" + cand + " portfolio=" + (this._staleness.portfolio ? 1 : 0)
             + " selection=" + (this._staleness.selection ? 1 : 0) + " towns=" + towns
             + " industries=" + industries + " engines=" + engines + " top=" + top);
  if (C39_DECISION_DELTA_PROBE && this._staleness.events > 0) {
    OpexC39Log("C39_DECISION_DELTA", "events=" + this._staleness.events + " top_before="
               + topBefore + " top_after=" + top + " top_changed=" + (topChanged ? 1 : 0));
    foreach (engine, mode in this._staleness.engineModes) {
      OpexC39Log("C39_ENGINE_DELTA", "engine=" + engine + " mode=" + mode + " retained="
                 + (OpexC39CatalogUsesEngine(this._catalog, engine.tointeger(), mode) ? 1 : 0)
                 + " top_changed=" + (topChanged ? 1 : 0));
      if (C39_AIR_REASON_PROBE && mode == "air") {
        local engineId = engine.tointeger();
        local planeType = AIEngine.IsValidEngine(engineId) ? AIEngine.GetPlaneType(engineId) : -1;
        local capacity = AIEngine.IsValidEngine(engineId) ? AIEngine.GetCapacity(engineId) : -1;
        OpexC39Log("C39_AIR_ENGINE_REASON", "engine=" + engine + " reason="
                   + OpexC39AirEngineReason(this._catalog, engineId) + " plane_type="
                   + planeType + " capacity=" + capacity);
      }
    }
  }
  /* C41.0 : le rebuild historique vient effectivement de refaire tout le catalogue et le
   * portefeuille ; il peut donc acquitter toutes les couches. Les micro-taches futures ne
   * copieront que leurs propres revisions. */
  if (C41_REVISION_PROBE) {
    /* C41.12 : publier AVANT de remettre les dates a blanc. Seules les revisions reellement
     * marquees ont un horodatage >= 0 ; une invalidation prefiltrée n'est pas un faux age. */
    if (C41_STALENESS_LEDGER) {
      foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
        local since = this._staleness.dirtySince.catalog[layer];
        if (since >= 0) {
          OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog." + layer + " method=full"
                              + " revision=" + this._staleness.revisions.catalog[layer]
                              + " age_days=" + (AIDate.GetCurrentDate() - since));
        }
      }
      foreach (layer in ["rail", "road", "air", "water"]) {
        local since = this._staleness.dirtySince.candidates[layer];
        if (since >= 0) {
          OpexC41StalenessLog("C41_STALENESS_ACK", "layer=candidates." + layer + " method=full"
                              + " revision=" + this._staleness.revisions.candidates[layer]
                              + " age_days=" + (AIDate.GetCurrentDate() - since));
        }
      }
      if (this._staleness.dirtySince.portfolio >= 0) {
        OpexC41StalenessLog("C41_STALENESS_ACK", "layer=portfolio method=full revision="
                            + this._staleness.revisions.portfolio + " age_days="
                            + (AIDate.GetCurrentDate() - this._staleness.dirtySince.portfolio));
      }
      if (this._staleness.dirtySince.selection >= 0) {
        OpexC41StalenessLog("C41_STALENESS_ACK", "layer=selection method=full revision="
                            + this._staleness.revisions.selection + " age_days="
                            + (AIDate.GetCurrentDate() - this._staleness.dirtySince.selection));
      }
    }
    this._staleness.acknowledged.catalog = {
      cargos = this._staleness.revisions.catalog.cargos, towns = this._staleness.revisions.catalog.towns,
      industries = this._staleness.revisions.catalog.industries, rail = this._staleness.revisions.catalog.rail,
      road = this._staleness.revisions.catalog.road, air = this._staleness.revisions.catalog.air,
      water = this._staleness.revisions.catalog.water,
    };
    this._staleness.acknowledged.candidates = {
      rail = this._staleness.revisions.candidates.rail, road = this._staleness.revisions.candidates.road,
      air = this._staleness.revisions.candidates.air, water = this._staleness.revisions.candidates.water,
    };
    this._staleness.acknowledged.portfolio = this._staleness.revisions.portfolio;
    this._staleness.acknowledged.selection = this._staleness.revisions.selection;
    if (this._staleness.events > 0) {
      OpexC39Log("C41_ACK", "reason=" + reason + " "
                 + OpexC41RevisionSnapshot(this._staleness.acknowledged)
                 + " water_staleness_age_days=" + waterAgeDays);
    }
  }
  this._staleness.catalog = { cargos = false, towns = false, industries = false, rail = false,
                              road = false, air = false, water = false };
  this._staleness.candidates = { rail = false, road = false, air = false, water = false };
  this._staleness.portfolio = false;
  this._staleness.selection = false;
  this._staleness.reasons = {};
  this._staleness.towns = {};
  this._staleness.industries = {};
  this._staleness.engines = {};
  this._staleness.engineModes = {};
  this._staleness.events = 0;
  this._staleness.topBefore = "none";
  this._staleness.topBeforeCaptured = false;
  this._staleness.waterCatalogDirtyDate = -1;
  this._staleness.waterCatalogDirtyTick = -1;
  this._staleness.dirtySince = {
    catalog = { cargos = -1, towns = -1, industries = -1, rail = -1, road = -1, air = -1, water = -1 },
    candidates = { rail = -1, road = -1, air = -1, water = -1 }, portfolio = -1, selection = -1,
  };
}

/* Event moteur exact : CRASH_TRAIN est emis dans train_cmd.cpp au moment ou deux trains
 * entrent en collision. XC garde la ligne, le vehicule, la tuile et les victimes ; RX reste le
 * filet annuel pour toute disparition sans evenement reconnu. */
function OpexAI::_processEvents()
{
  while (AIEventController.IsEventWaiting()) {
    local event = AIEventController.GetNextEvent();
    if (event == null) continue;
    local eventType = event.GetEventType();

    if (eventType == AIEvent.ET_VEHICLE_CRASHED) {
      local crash = AIEventVehicleCrashed.Convert(event);
      if (crash != null && crash.GetCrashReason() == AIEventVehicleCrashed.CRASH_TRAIN) {
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
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT) {
      if (EVENT_DEPOT_SELL && this._vehiclesToScrap != null) {
        local depotEvt = AIEventVehicleWaitingInDepot.Convert(event);
        if (depotEvt != null) {
          local vehicle = depotEvt.GetVehicleID();
          if (vehicle in this._vehiclesToScrap) {
            local lineId = this._vehiclesToScrap[vehicle];
            if (AIVehicle.IsValidVehicle(vehicle) && AIVehicle.IsStoppedInDepot(vehicle)) {
              if (AIVehicle.SellVehicle(vehicle)) {
                if (DECISION_LOG) {
                  OpexDecide("SCRAP_LINE", "action=event_sell line=" + lineId + " vehicle=" + vehicle);
                }
                delete this._vehiclesToScrap[vehicle];
              }
            }
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_INDUSTRY_CLOSE) {
      if (C39_INVALIDATION_PROBE) {
        local probeEvt = AIEventIndustryClose.Convert(event);
        if (probeEvt != null) {
          this._markDirty("industry_close", ["industries"], ["rail", "road"], true, true,
                          "industry", probeEvt.GetIndustryID());
        }
      }
      if (EVENT_INDUSTRY_CLOSE) {
        local indEvt = AIEventIndustryClose.Convert(event);
        if (indEvt != null) {
          local indId = indEvt.GetIndustryID();
          if (DECISION_LOG) {
            OpexDecide("EVENT_INDUSTRY_CLOSE", "industry=" + indId);
          }
          foreach (line in this._lines) {
            local srcInd = ("srcIndustry" in line) ? line.srcIndustry : -1;
            local dstInd = ("dstIndustry" in line) ? line.dstIndustry : -1;
            if (srcInd == indId || dstInd == indId) {
              this._triggerScrapLine(line, "industry_close");
            }
          }
          if (this._catalog != null) {
            this._catalog._refreshIndustries();
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_OFFER) {
      if (EVENT_SUBSIDY_PROBE) {
        local subEvt = AIEventSubsidyOffer.Convert(event);
        if (subEvt != null) {
          local subId = subEvt.GetSubsidyID();
          if (AISubsidy.IsValidSubsidy(subId)) {
            local cargo = AISubsidy.GetCargoType(subId);
            local srcType = AISubsidy.GetSourceType(subId);
            local srcId = AISubsidy.GetSourceIndex(subId);
            local dstType = AISubsidy.GetDestinationType(subId);
            local dstId = AISubsidy.GetDestinationIndex(subId);
            local expDate = AISubsidy.GetExpireDate(subId);
            local mult = AIGameSettings.IsValid("difficulty.subsidy_multiplier") ? AIGameSettings.GetValue("difficulty.subsidy_multiplier") : -1;
            local dur = AIGameSettings.IsValid("difficulty.subsidy_duration") ? AIGameSettings.GetValue("difficulty.subsidy_duration") : -1;

            local matchedLine = -1;
            foreach (line in this._lines) {
              if (line.cargo != cargo) continue;
              local mSrc = false;
              local mDst = false;
              if (srcType == AISubsidy.SPT_INDUSTRY && ("srcIndustry" in line) && line.srcIndustry == srcId) mSrc = true;
              else if (srcType == AISubsidy.SPT_TOWN && ("originA" in line) && line.originA == srcId) mSrc = true;
              if (dstType == AISubsidy.SPT_INDUSTRY && ("dstIndustry" in line) && line.dstIndustry == dstId) mDst = true;
              else if (dstType == AISubsidy.SPT_TOWN && ("originB" in line) && line.originB == dstId) mDst = true;
              if (mSrc && mDst) { matchedLine = line.lineId; break; }
            }

            if (this._subsidyStats != null) {
              this._subsidyStats.offers++;
              if (matchedLine >= 0) this._subsidyStats.matchedPool++;
            }
            if (this._activeSubsidies != null) {
              this._activeSubsidies.rawset(subId, {
                cargo = cargo, srcType = srcType, srcId = srcId,
                dstType = dstType, dstId = dstId, expDate = expDate,
                matchedLine = matchedLine
              });
            }

            if (DECISION_LOG) {
              local cName = AICargo.GetCargoLabel(cargo);
              OpexDecide("SUBSIDY_OFFER", "sub=" + subId + " cargo=" + cName + " src_t=" + srcType + " src=" + srcId + " dst_t=" + dstType + " dst=" + dstId + " exp=" + expDate + " mult=" + mult + " dur=" + dur + " matched=" + (matchedLine >= 0 ? matchedLine : "none"));
            }
            local year = AIDate.GetYear(AIDate.GetCurrentDate());
            OpexSign(AIMap.GetTileIndex(1, 1), "SO|" + (year % 100) + "|" + subId + "|" + cargo + "|" + (matchedLine >= 0 ? 1 : 0));
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED) {
      if (EVENT_SUBSIDY_PROBE) {
        local subEvt = AIEventSubsidyOfferExpired.Convert(event);
        if (subEvt != null) {
          local subId = subEvt.GetSubsidyID();
          if (this._subsidyStats != null) {
            this._subsidyStats.expiredWithoutAward++;
          }
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          if (DECISION_LOG) {
            OpexDecide("SUBSIDY_OFFER_EXPIRED", "sub=" + subId);
          }
          local year = AIDate.GetYear(AIDate.GetCurrentDate());
          OpexSign(AIMap.GetTileIndex(1, 1), "SE|" + (year % 100) + "|" + subId);
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_AWARDED) {
      if (EVENT_SUBSIDY_PROBE) {
        local subEvt = AIEventSubsidyAwarded.Convert(event);
        if (subEvt != null) {
          local subId = subEvt.GetSubsidyID();
          local company = AISubsidy.IsValidSubsidy(subId) ? AISubsidy.GetAwardedTo(subId) : -1;
          local isSelf = (company == AICompany.COMPANY_SELF);
          if (this._subsidyStats != null) {
            if (isSelf) this._subsidyStats.awardedSelf++;
            else this._subsidyStats.awardedOther++;
          }
          if (DECISION_LOG) {
            OpexDecide("SUBSIDY_AWARDED", "sub=" + subId + " company=" + company + " is_self=" + (isSelf ? 1 : 0));
          }
          local year = AIDate.GetYear(AIDate.GetCurrentDate());
          OpexSign(AIMap.GetTileIndex(1, 1), "SA|" + (year % 100) + "|" + subId + "|" + (isSelf ? 1 : 0));
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_EXPIRED) {
      if (EVENT_SUBSIDY_PROBE) {
        local subEvt = AIEventSubsidyExpired.Convert(event);
        if (subEvt != null) {
          local subId = subEvt.GetSubsidyID();
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          if (DECISION_LOG) {
            OpexDecide("SUBSIDY_EXPIRED", "sub=" + subId);
          }
          local year = AIDate.GetYear(AIDate.GetCurrentDate());
          OpexSign(AIMap.GetTileIndex(1, 1), "SX|" + (year % 100) + "|" + subId);
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_LOST) {
      /* C41.4 : mesurer d'abord la qualite de l'attribution evenement -> ligne avant de
       * concevoir une reparation. La lecture de _lines est volontairement directe : un
       * vehicule absent de cette persistance est un orphelin a compter, pas a deviner via
       * une recherche de stations couteuse. */
      if (C41_VEHICLE_LOST_PROBE) {
        local probeEvt = AIEventVehicleLost.Convert(event);
        if (probeEvt != null) {
          local probeVehicle = probeEvt.GetVehicleID();
          local probeLine = OpexC41PersistedLineForVehicle(this._lines, probeVehicle);
          local probeLineId = probeLine != null ? probeLine.lineId : -1;
          local probeMode = probeLine != null && ("mode" in probeLine) ? probeLine.mode : "orphan";
          local probeValid = AIVehicle.IsValidVehicle(probeVehicle);
          OpexC41VehicleLostLog("vehicle=" + probeVehicle +
                                " valid=" + (probeValid ? 1 : 0) +
                                " line=" + probeLineId + " mode=" + probeMode +
                                " orphan=" + (probeLineId < 0 ? 1 : 0));
          /* C41.5 : seuls les Lost rail attribues et encore vivants ont des ordres et un depot
           * interpretables. `target_line` dit un fait (destination de l'ordre dans les deux
           * gares persistees), jamais que la voie est praticable. */
          if (C41_RAIL_LOST_PROBE && probeValid && probeLine != null && probeMode == "rail") {
            local orderCount = AIOrder.GetOrderCount(probeVehicle);
            local currentOrder = AIOrder.ResolveOrderPosition(probeVehicle, AIOrder.ORDER_CURRENT);
            local orderValid = currentOrder >= 0 && currentOrder < orderCount
                && AIOrder.IsValidVehicleOrder(probeVehicle, currentOrder);
            local target = orderValid ? AIOrder.GetOrderDestination(probeVehicle, currentOrder) : -1;
            local targetStation = AIMap.IsValidTile(target) ? AIStation.GetStationID(target) : -1;
            local stationA = OpexLineStationId(probeLine, "A");
            local stationB = OpexLineStationId(probeLine, "B");
            local targetLine = targetStation == stationA || targetStation == stationB;
            local location = AIVehicle.GetLocation(probeVehicle);
            local depot = ("depot" in probeLine) && probeLine.depot != null ? probeLine.depot : -1;
            local depotValid = AIMap.IsValidTile(depot) && AIRail.IsRailDepotTile(depot);
            OpexC41RailLostLog("vehicle=" + probeVehicle + " line=" + probeLineId
                               + " state=" + AIVehicle.GetState(probeVehicle)
                               + " orders=" + orderCount + " current=" + currentOrder
                               + " order_valid=" + (orderValid ? 1 : 0)
                               + " target=" + target + " target_line=" + (targetLine ? 1 : 0)
                               + " location=" + location
                               + " location_rail=" + (AIMap.IsValidTile(location) && AIRail.IsRailTile(location) ? 1 : 0)
                               + " location_depot=" + (AIMap.IsValidTile(location) && AIRail.IsRailDepotTile(location) ? 1 : 0)
                               + " depot=" + depot + " depot_valid=" + (depotValid ? 1 : 0));
            /* C41.6 : uniquement les attributs deja stockes a la construction/extension. Les
             * compteurs de signaux ne le sont pas ; les inventer ou rescanner le trace serait une
             * autre sonde, pas une propriete de cette ligne. */
            if (C41_RAIL_LOST_TOPOLOGY_PROBE) {
              local depot2 = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
              local depot2Valid = AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2);
              local vehicleCount = ("vehicles" in probeLine) && probeLine.vehicles != null
                  ? probeLine.vehicles.len() : 0;
              OpexC41RailLostTopologyLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                         + " double_track=" + (("doubleTrack" in probeLine && probeLine.doubleTrack == 1) ? 1 : 0)
                                         + " depot2_valid=" + (depot2Valid ? 1 : 0)
                                         + " platform=" + (("platformLength" in probeLine) ? probeLine.platformLength : 0)
                                         + " vehicles=" + vehicleCount
                                         + " trains=" + (("trains" in probeLine) ? probeLine.trains : 0)
                                         + " wagons=" + (("wagons" in probeLine) ? probeLine.wagons : 0)
                                         + " kind=" + (("kind" in probeLine) ? probeLine.kind : "unknown"));
            }
            if (C41_RAIL_LOST_PHYSICAL_PROBE) {
              local approachA = OpexC41RailApproachFacts(("platformA" in probeLine) ? probeLine.platformA : null);
              local approachB = OpexC41RailApproachFacts(("platformB" in probeLine) ? probeLine.platformB : null);
              local approachA2 = OpexC41RailApproachFacts(("platformA2" in probeLine) ? probeLine.platformA2 : null,
                                                          ("stationA2" in probeLine) ? probeLine.stationA2 : null);
              local approachB2 = OpexC41RailApproachFacts(("platformB2" in probeLine) ? probeLine.platformB2 : null,
                                                          ("stationB2" in probeLine) ? probeLine.stationB2 : null);
              local depotFacts = OpexC41RailDepotFrontFacts(depot);
              local depot2Tile = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
              local depot2Facts = OpexC41RailDepotFrontFacts(depot2Tile);
              OpexC41RailLostPhysicalLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                         + " a_rail=" + approachA.rail + " a_tracks=" + approachA.tracks + " a_signal=" + approachA.signal
                                         + " b_rail=" + approachB.rail + " b_tracks=" + approachB.tracks + " b_signal=" + approachB.signal
                                         + " a2_rail=" + approachA2.rail + " a2_tracks=" + approachA2.tracks + " a2_signal=" + approachA2.signal
                                         + " b2_rail=" + approachB2.rail + " b2_tracks=" + approachB2.tracks + " b2_signal=" + approachB2.signal
                                         + " depot_front_rail=" + depotFacts.rail + " depot_front_tracks=" + depotFacts.tracks
                                         + " depot2_front_rail=" + depot2Facts.rail + " depot2_front_tracks=" + depot2Facts.tracks);
            }
            if (C41_RAIL_LOST_CONNECTIVITY_PROBE) {
              local exitA = ("platformA" in probeLine && probeLine.platformA != null && ("station_exit" in probeLine.platformA)) ? probeLine.platformA.station_exit : null;
              local exitB = ("platformB" in probeLine && probeLine.platformB != null && ("station_exit" in probeLine.platformB)) ? probeLine.platformB.station_exit : null;
              local leadA = OpexC41RailApproachLead(("platformA" in probeLine) ? probeLine.platformA : null);
              local leadB = OpexC41RailApproachLead(("platformB" in probeLine) ? probeLine.platformB : null);
              local leadA2 = OpexC41RailApproachLead(("platformA2" in probeLine) ? probeLine.platformA2 : null,
                                                     ("stationA2" in probeLine) ? probeLine.stationA2 : null);
              local leadB2 = OpexC41RailApproachLead(("platformB2" in probeLine) ? probeLine.platformB2 : null,
                                                     ("stationB2" in probeLine) ? probeLine.stationB2 : null);
              local a = OpexC41RailLocalLinks(leadA, exitA);
              local b = OpexC41RailLocalLinks(leadB, exitB);
              local a2 = OpexC41RailLocalLinks(leadA2, ("stationA2" in probeLine) ? probeLine.stationA2 : null);
              local b2 = OpexC41RailLocalLinks(leadB2, ("stationB2" in probeLine) ? probeLine.stationB2 : null);
              local front = depotValid ? AIRail.GetRailDepotFrontTile(depot) : null;
              local depotLinks = OpexC41RailLocalLinks(front, depot);
              local depot2 = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
              local front2 = AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2) ? AIRail.GetRailDepotFrontTile(depot2) : null;
              local depot2Links = OpexC41RailLocalLinks(front2, depot2);
              local vehicleLinks = OpexC41RailLocalLinks(location);
              OpexC41RailLostConnectivityLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                             + " a_branches=" + a.branches + " a_links=" + a.links
                                             + " b_branches=" + b.branches + " b_links=" + b.links
                                             + " a2_branches=" + a2.branches + " a2_links=" + a2.links
                                             + " b2_branches=" + b2.branches + " b2_links=" + b2.links
                                             + " depot_branches=" + depotLinks.branches + " depot_links=" + depotLinks.links
                                             + " depot2_branches=" + depot2Links.branches + " depot2_links=" + depot2Links.links
                                             + " vehicle_rail=" + vehicleLinks.rail + " vehicle_branches=" + vehicleLinks.branches);
            }
            /* C41.8 : l'evenement ne construit rien. Il coalesce l'identite stable de la ligne
             * et reveille la micro-tache qui executera au plus une reparation ciblee. */
            if (C41_RAIL_LOST_SIGNAL_REPAIR && ("doubleTrack" in probeLine) && probeLine.doubleTrack == 1 &&
                this._c41RailSignalLines != null) {
              this._c41RailSignalLines.rawset("" + probeLineId, true);
              if (this._taskQueue != null) {
                foreach (signalTask in this._taskQueue) {
                  if (signalTask.name == "c41_rail_signals") {
                    signalTask.enabled = true;
                    signalTask.dueCycle = this._taskCycle;
                    break;
                  }
                }
              }
              OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_ARM", "line=" + probeLineId + " vehicle=" + probeVehicle);
            }
            /* C41.10 : arme independamment de C41.8 -- raccord manquant et signal manquant sont
             * deux causes distinctes du meme VehicleLost. Meme schema de coalescage. */
            if (C41_RAIL_LOST_JUNCTION_REPAIR && ("doubleTrack" in probeLine) && probeLine.doubleTrack == 1 &&
                this._c41RailJunctionLines != null) {
              this._c41RailJunctionLines.rawset("" + probeLineId, true);
              if (this._taskQueue != null) {
                foreach (junctionTask in this._taskQueue) {
                  if (junctionTask.name == "c41_rail_junction") {
                    junctionTask.enabled = true;
                    junctionTask.dueCycle = this._taskCycle;
                    break;
                  }
                }
              }
              OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_ARM", "line=" + probeLineId + " vehicle=" + probeVehicle);
            }
          }
        }
      }
      if (EVENT_VEHICLE_LOST) {
        local lostEvt = AIEventVehicleLost.Convert(event);
        if (lostEvt != null) {
          local vehicle = lostEvt.GetVehicleID();
          if (AIVehicle.IsValidVehicle(vehicle)) {
            local lineId = -1;
            local vehicleType = AIVehicle.GetVehicleType(vehicle);
            foreach (line in this._lines) {
              if (!("vehicles" in line)) continue;
              foreach (v in line.vehicles) {
                if (v == vehicle) {
                  lineId = line.lineId;
                  if (!("lostCount" in line)) line.lostCount <- 0;
                  line.lostCount++;
                  break;
                }
              }
              if (lineId >= 0) break;
            }
            local loc = AIVehicle.GetLocation(vehicle);
            if (DECISION_LOG) {
              OpexDecide("VEHICLE_LOST", "vehicle=" + vehicle + " line=" + lineId + " type=" + vehicleType + " tile=" + loc);
            }
            local year = AIDate.GetYear(AIDate.GetCurrentDate());
            OpexSign(AIMap.GetTileIndex(1, 1), "VL|" + (year % 100) + "|" + lineId + "|" + vehicle);
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_INDUSTRY_OPEN) {
      if (C39_INVALIDATION_PROBE) {
        local probeEvt = AIEventIndustryOpen.Convert(event);
        if (probeEvt != null) {
          this._markDirty("industry_open", ["industries"], ["rail", "road"], true, true,
                          "industry", probeEvt.GetIndustryID());
        }
      }
      if (EVENT_CATALOG_INVALIDATE) {
        local indEvt = AIEventIndustryOpen.Convert(event);
        if (indEvt != null) {
          local indId = indEvt.GetIndustryID();
          if (AIIndustry.IsValidIndustry(indId)) {
            local indType = AIIndustry.GetIndustryType(indId);
            if (DECISION_LOG) {
              OpexDecide("EVENT_INDUSTRY_OPEN", "industry=" + indId + " type=" + indType);
            }
            local year = AIDate.GetYear(AIDate.GetCurrentDate());
            OpexSign(AIMap.GetTileIndex(1, 1), "IO|" + (year % 100) + "|" + indId + "|" + indType);
            if (this._catalog != null) {
              this._catalog._refreshIndustries();
            }
            this._portfolioInvalidated = true;
            if (this._taskQueue != null) {
              foreach (t in this._taskQueue) {
                if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
              }
            }
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_TOWN_FOUNDED) {
      if (C39_INVALIDATION_PROBE) {
        local probeEvt = AIEventTownFounded.Convert(event);
        if (probeEvt != null) {
          this._markDirty("town_founded", ["towns"], ["rail", "road", "air", "water"],
                          true, true, "town", probeEvt.GetTownID());
        }
      }
      if (EVENT_CATALOG_INVALIDATE) {
        local townEvt = AIEventTownFounded.Convert(event);
        if (townEvt != null) {
          local townId = townEvt.GetTownID();
          if (AITown.IsValidTown(townId)) {
            local pop = AITown.GetPopulation(townId);
            if (DECISION_LOG) {
              OpexDecide("EVENT_TOWN_FOUNDED", "town=" + townId + " pop=" + pop);
            }
            local year = AIDate.GetYear(AIDate.GetCurrentDate());
            OpexSign(AIMap.GetTileIndex(1, 1), "TF|" + (year % 100) + "|" + townId + "|" + pop);
            if (this._catalog != null) {
              this._catalog._refreshTowns();
            }
            this._portfolioInvalidated = true;
            if (this._taskQueue != null) {
              foreach (t in this._taskQueue) {
                if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
              }
            }
          }
        }
      }
      continue;
    }

    if (eventType == AIEvent.ET_ENGINE_AVAILABLE) {
      this._recomputeEpochBounds = true;
      if (this._catalog != null) OpexRefreshEpochBounds(this._catalog);
      if (C39_INVALIDATION_PROBE || C39_ENGINE_REFRESH) {
        local engineEvt = AIEventEngineAvailable.Convert(event);
        if (engineEvt != null) {
          local engine = engineEvt.GetEngineID();
          local vehicleType = AIEngine.IsValidEngine(engine) ? AIEngine.GetVehicleType(engine) : -1;
          local mode = null;
          if (vehicleType == AIVehicle.VT_RAIL) mode = "rail";
          else if (vehicleType == AIVehicle.VT_ROAD) mode = "road";
          else if (vehicleType == AIVehicle.VT_AIR) mode = "air";
          else if (vehicleType == AIVehicle.VT_WATER) mode = "water";
          if (mode != null) {
            /* La sonde reste la seule à conserver l'état/les IDs. C39.2 consomme le chemin
             * historique sans changer les cas industrie déjà couverts par P3. */
            if (C39_INVALIDATION_PROBE) {
              /* C41.2 ne consulte le predicat que pour son bras actif ; C39 conserve toujours
               * la trace exhaustive de l'evenement, y compris un moteur ensuite filtre. */
              local targetedRelevant = !(C41_WATER_REFRESH && C41_WATER_PRECHECK && mode == "water")
                  || this._catalog.isWaterEngineRelevant(engine);
              this._markDirty("engine_available", [mode], [mode], true, true, "engine", engine,
                              mode, targetedRelevant);
            }
            if (C39_ENGINE_REFRESH) {
              this._portfolioInvalidated = true;
              if (this._taskQueue != null) {
                foreach (t in this._taskQueue) {
                  if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
                }
              }
            }
          }
        }
      }
      continue;
    }
  }
}

/* C41.11 : enveloppe strictement observatoire. `slack_ops_used` est borne au reliquat disponible
 * au debut du passage : un calcul qui franchit un tick ne transforme pas les ticks suivants en
 * slack retroactif. Les continuations rail precedant la selection sont rangees explicitement par
 * nature, afin de ne pas les attribuer abusivement a la tache choisie ensuite. Si les deux etats
 * coexistent, une categorie jointe conserve l'incertitude plutot que de fabriquer une attribution. */
function OpexAI::_runNextTaskWithSlackLedger()
{
  if ((!C41_SLACK_LEDGER && !C41_MONTHLY_BUSY_LEDGER && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER
       && !C41_RAIL_SLICE_LEDGER && !C39_PASS_CLOCK_LEDGER)
      || this._c41SlackLedger == null) {
    return this._runNextTask();
  }
  if (C41_MONTHLY_BUSY_LEDGER) {
    local date = AIDate.GetCurrentDate();
    local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
    if (this._c41MonthlyBusyMonth != ym) {
      if (this._c41MonthlyBusyMonth >= 0) this._logC41MonthlyBusyLedger();
      this._c41MonthlyBusyMonth = ym;
      this._c41MonthlyBusyLedger = {};
    }
  }
  local mark = OpexOpsMeasureBegin();
  /* C39.6 : date AVANT l'appel mesure, pour le delta jours de la passe entiere. mark.tick sert
   * aussi de tick de depart : pas de second AIController.GetTick(), c'est deja celui capture par
   * OpexOpsMeasureBegin() ci-dessus. */
  local c39DateBefore = C39_PASS_CLOCK_LEDGER ? AIDate.GetCurrentDate() : -1;
  local continuationCategory = null;
  if (this._railExpansion != null && this._railSearch != null) {
    continuationCategory = "rail_expansion+rail_search";
  } else if (this._railSearch != null) {
    continuationCategory = "rail_search";
  } else if (this._railExpansion != null) {
    continuationCategory = "rail_expansion";
  }
  local ran = this._runNextTask();
  local ops = OpexOpsMeasureEnd(mark);
  local category = continuationCategory != null ? continuationCategory : this._c41LastTaskName;
  if (category == null) category = "idle";
  if (C41_SLACK_LEDGER) {
    local entry = (category in this._c41SlackLedger) ? this._c41SlackLedger[category]
        : { calls = 0, ran = 0, ops = 0, slackAvailable = 0, slackUsed = 0, slackLeft = 0 };
    entry.calls++;
    if (ran) entry.ran++;
    entry.ops += ops;
    entry.slackAvailable += mark.left;
    entry.slackUsed += ops < mark.left ? ops : mark.left;
    entry.slackLeft += ops < mark.left ? mark.left - ops : 0;
    this._c41SlackLedger.rawset(category, entry);
  }
  if (C41_MONTHLY_BUSY_LEDGER) {
    local entry = (category in this._c41MonthlyBusyLedger) ? this._c41MonthlyBusyLedger[category]
        : { calls = 0, ran = 0, ops = 0 };
    entry.calls++;
    if (ran) entry.ran++;
    entry.ops += ops;
    this._c41MonthlyBusyLedger.rawset(category, entry);
  }
  /* C41.46 : this._c41RailSliceLastOps a ete mesure INDEPENDAMMENT dans _runNextTask, pendant le
   * meme appel que `ops` ci-dessus (OpexOpsMeasureBegin/End ne partagent aucun etat -- imbrication
   * sure, voir budget.nut). Sentinelle -1 = aucune tranche A* cette passe. La difference donne les
   * opcodes de la tache de file jouee dans la MEME passe, jamais mesures separement jusqu'ici. */
  if (C41_RAIL_SLICE_LEDGER && this._c41RailSliceLastOps >= 0) {
    local taskOps = ops - this._c41RailSliceLastOps;
    if (taskOps < 0) taskOps = 0;
    this._recordC41RailSliceLedger(this._c41RailSliceLastOps, taskOps,
                                   this._c41RailSliceLastIterDelta, this._c41RailSliceLastDone);
  }
  /* C39.6 : this._c39PassClockSlice{Days,Ticks,Ops} ont ete mesures INDEPENDAMMENT dans
   * _runNextTask, pendant le meme appel que `ops`/`c39DateBefore` ci-dessus (meme garantie de
   * non-partage d'etat que C41.46). Sentinelle -1 sur _c39PassClockSliceOps = aucune tranche A*
   * cette passe -- la cle "|slice" contre "|noslice" porte cette information, les trois champs
   * slice_* valent alors 0. La cle est this._c41LastTaskName ("idle" si nul), PAS `category` :
   * `category` fusionne les continuations rail (C41.11), alors qu'ici la tranche est deja portee
   * separement par la cle slice/noslice et on veut le nom de la VRAIE tache de file. ⚠️ Sous
   * loop_budget=0 (defaut), la boucle principale fait un Sleep(1) APRES cet appel mesure : ce
   * Sleep n'est donc jamais compte dans days/ticks. A 74 ticks/jour c'est negligeable devant les
   * 3,6 jours mesures (docs/05_cadence_projects_rail_search.md §4.3), mais le prochain lecteur
   * doit le savoir. */
  if (C39_PASS_CLOCK_LEDGER) {
    local passDays = AIDate.GetCurrentDate() - c39DateBefore;
    local passTicks = AIController.GetTick() - mark.tick;
    local hasSlice = this._c39PassClockSliceOps >= 0;
    local taskName = this._c41LastTaskName != null ? this._c41LastTaskName : "idle";
    local c39Key = taskName + "|" + (hasSlice ? "slice" : "noslice");
    this._recordC39PassClockLedger(c39Key, passDays, passTicks, ops,
        hasSlice ? this._c39PassClockSliceDays : 0,
        hasSlice ? this._c39PassClockSliceTicks : 0,
        hasSlice ? this._c39PassClockSliceOps : 0);
  }
  /* C41.13 : apres la tache historique, seules les couches encore sales sont admissibles au
   * delestage. Une meme tranche peut etre une opportunite pour plusieurs couches : le total par
   * couche n'est donc volontairement pas un budget global, mais une borne superieure par choix. */
  this._recordC41StaleOpportunity(ops < mark.left ? mark.left - ops : 0);
  return ran;
}

/* Publie a l'entree du mois suivant : ainsi toutes les tranches du mois clos sont attribuees
 * a leur tache effective, y compris une continuation rail qui precede la file. */
function OpexAI::_logC41MonthlyBusyLedger()
{
  if (!C41_MONTHLY_BUSY_LEDGER || this._c41MonthlyBusyLedger == null) return;
  local year = this._c41MonthlyBusyMonth / 12;
  local month = this._c41MonthlyBusyMonth % 12 + 1;
  foreach (task, entry in this._c41MonthlyBusyLedger) {
    OpexC41SchedulerLog("C41_MONTH_BUSY", "year=" + year + " month=" + month + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops);
  }
}

/* Publication annuelle, hors des passages mesures : au plus une ligne par categorie et par an.
 * Reset apres publication afin que chaque ligne decrive une fenetre comparable. */
function OpexAI::_logC41SlackLedger(year)
{
  if (!C41_SLACK_LEDGER || this._c41SlackLedger == null) return;
  foreach (task, entry in this._c41SlackLedger) {
    OpexC41SchedulerLog("C41_SLACK_LEDGER", "year=" + year + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops
                        + " slack_ops_available=" + entry.slackAvailable
                        + " slack_ops_used=" + entry.slackUsed
                        + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41SlackLedger = {};
}

/* C41.13 : photographie sans cout de carte ni de catalogue. Les dates sont posees seulement par
 * C41.0 au premier evenement d'une rafale ; une couche sans date ne produit donc pas de faux
 * point de fraicheur. */
function OpexAI::_recordC41StaleOpportunity(slackLeft)
{
  if ((!C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) || this._staleness == null) return;
  local now = AIDate.GetCurrentDate();
  foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.catalog[layer];
    if (since < 0) continue;
    local key = "catalog." + layer;
    if (C41_OPPORTUNITY_LEDGER && this._c41OpportunityLedger != null) {
      local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
          : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
      local age = now - since;
      entry.observations++;
      entry.staleDays += age;
      if (age > entry.maxStaleDays) entry.maxStaleDays = age;
      entry.slackLeft += slackLeft;
      this._c41OpportunityLedger.rawset(key, entry);
    }
    local hint = OpexC41MicrotaskOpsHint(key);
    if (C41_ADMISSION_LEDGER && hint > 0 && this._c41AdmissionLedger != null) {
      local admission = (key in this._c41AdmissionLedger) ? this._c41AdmissionLedger[key]
          : { checks = 0, fits = 0, maxSlackLeft = 0, targetOps = hint };
      admission.checks++;
      if (slackLeft >= hint) admission.fits++;
      if (slackLeft > admission.maxSlackLeft) admission.maxSlackLeft = slackLeft;
      this._c41AdmissionLedger.rawset(key, admission);
    }
  }
  foreach (layer in ["rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.candidates[layer];
    if (since < 0) continue;
    local key = "candidates." + layer;
    local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(key, entry);
  }
  foreach (layer in ["portfolio", "selection"]) {
    local since = this._staleness.dirtySince[layer];
    if (since < 0) continue;
    local entry = (layer in this._c41OpportunityLedger) ? this._c41OpportunityLedger[layer]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(layer, entry);
  }
}

function OpexAI::_logC41AdmissionLedger(year)
{
  if (!C41_ADMISSION_LEDGER || this._c41AdmissionLedger == null) return;
  foreach (layer, entry in this._c41AdmissionLedger) {
    OpexC41SchedulerLog("C41_ADMISSION_LEDGER", "year=" + year + " layer=" + layer
                        + " target_ops=" + entry.targetOps + " checks=" + entry.checks
                        + " fits=" + entry.fits + " max_slack_ops_left=" + entry.maxSlackLeft);
  }
  this._c41AdmissionLedger = {};
}

function OpexAI::_logC41OpportunityLedger(year)
{
  if (!C41_OPPORTUNITY_LEDGER || this._c41OpportunityLedger == null) return;
  foreach (layer, entry in this._c41OpportunityLedger) {
    OpexC41SchedulerLog("C41_OPPORTUNITY_LEDGER", "year=" + year + " layer=" + layer
                        + " observations=" + entry.observations + " stale_days_sum=" + entry.staleDays
                        + " max_stale_days=" + entry.maxStaleDays + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41OpportunityLedger = {};
}

/* C41.46 : accumulateur UNIQUE (pas par categorie, contrairement aux autres ledgers C41) -- il
 * n'existe qu'un seul canal de recherche rail a la fois (this._railSearch), donc rien a ventiler. */
function OpexAI::_recordC41RailSliceLedger(netOps, taskOps, iterDelta, done)
{
  if (this._c41RailSliceLedger == null) {
    this._c41RailSliceLedger = { calls = 0, notDoneCalls = 0, netOps = 0, taskOps = 0, iterDelta = 0 };
  }
  local entry = this._c41RailSliceLedger;
  entry.calls++;
  if (!done) entry.notDoneCalls++;
  entry.netOps += netOps;
  entry.taskOps += taskOps;
  entry.iterDelta += iterDelta;
}

/* Publication annuelle, comme C41.11. `not_done_calls` = tranches qui n'ont PAS atteint
 * slice.done (recherche toujours en "search" apres l'appel) ; calls - not_done_calls = tranches
 * qui ont termine leur recherche (transition vers phase "build") cette annee. */
function OpexAI::_logC41RailSliceLedger(year)
{
  if (!C41_RAIL_SLICE_LEDGER || this._c41RailSliceLedger == null
      || this._c41RailSliceLedger.calls == 0) {
    this._c41RailSliceLedger = null;
    return;
  }
  local entry = this._c41RailSliceLedger;
  OpexC41RailSliceLog("year=" + year + " calls=" + entry.calls
                      + " not_done_calls=" + entry.notDoneCalls
                      + " net_ops=" + entry.netOps + " task_ops=" + entry.taskOps
                      + " iter_delta=" + entry.iterDelta);
  this._c41RailSliceLedger = null;
}

/* C39.6 : accumulateur PAR CLE (contrairement a C41.46, canal rail unique) -- la cle croise le
 * nom de tache de file et la presence d'une tranche A* dans la meme passe. */
function OpexAI::_recordC39PassClockLedger(key, days, ticks, ops, sliceDays, sliceTicks, sliceOps)
{
  if (this._c39PassClockLedger == null) this._c39PassClockLedger = {};
  local entry = (key in this._c39PassClockLedger) ? this._c39PassClockLedger[key]
      : { passes = 0, days = 0, ticks = 0, ops = 0, sliceDays = 0, sliceTicks = 0, sliceOps = 0 };
  entry.passes++;
  entry.days += days;
  entry.ticks += ticks;
  entry.ops += ops;
  entry.sliceDays += sliceDays;
  entry.sliceTicks += sliceTicks;
  entry.sliceOps += sliceOps;
  this._c39PassClockLedger.rawset(key, entry);
}

/* Publication annuelle, comme les autres ledgers C39/C41 : une ligne par cle, reset apres
 * publication pour que chaque ligne decrive une fenetre comparable (meme motif que
 * _logC41SlackLedger / _logC41RailSliceLedger). */
function OpexAI::_logC39PassClockLedger(year)
{
  if (!C39_PASS_CLOCK_LEDGER || this._c39PassClockLedger == null) return;
  foreach (key, entry in this._c39PassClockLedger) {
    OpexC39PassClockLog("phase=annual year=" + year + " key=" + key
                        + " passes=" + entry.passes + " days=" + entry.days
                        + " ticks=" + entry.ticks + " ops=" + entry.ops
                        + " slice_days=" + entry.sliceDays + " slice_ticks=" + entry.sliceTicks
                        + " slice_ops=" + entry.sliceOps);
  }
  this._c39PassClockLedger = {};
}

/* C48 : les ops par tentative sont volontairement imbriques dans ops_total de la passe. La
 * soustraction faite au depouillement mesure le cout hors tentative (balayage, A*, logs) ; ce
 * n'est pas un double comptage a "corriger". */
function OpexAI::_recordC48AttemptLedger(mode, outcome, rank, ops, days)
{
  if (this._c48AttemptLedger == null) this._c48AttemptLedger = {};
  local key = mode + "|" + outcome;
  local entry = (key in this._c48AttemptLedger) ? this._c48AttemptLedger[key]
      : { attempts = 0, ops = 0, days = 0, rankSum = 0 };
  entry.attempts++;
  entry.ops += ops;
  entry.days += days;
  entry.rankSum += rank;
  this._c48AttemptLedger.rawset(key, entry);
}

function OpexAI::_recordC48PassLedger(attemptsTotal, opsTotal, built, bestLen, maxRank)
{
  if (this._c48PassLedger == null) this._c48PassLedger = {};
  local entry = ("pass" in this._c48PassLedger) ? this._c48PassLedger.pass
      : { passes = 0, attemptsTotal = 0, opsTotal = 0, built = 0, bestLenSum = 0, maxRankSum = 0 };
  entry.passes++;
  entry.attemptsTotal += attemptsTotal;
  entry.opsTotal += opsTotal;
  if (built) entry.built++;
  entry.bestLenSum += bestLen;
  entry.maxRankSum += maxRank;
  this._c48PassLedger.rawset("pass", entry);
}

/* La tache report passe au premier tour de l'annee suivante : year=1971 decrit donc 1970, et
 * la derniere annee de partie n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexAI::_logC48ProjectAttemptLedger(year)
{
  if (!C48_PROJECT_ATTEMPT_LEDGER) return;
  if (this._c48AttemptLedger != null) {
    foreach (key, entry in this._c48AttemptLedger) {
      OpexC48ProjectAttemptLog("phase=annual year=" + year + " key=" + key
          + " attempts=" + entry.attempts + " ops=" + entry.ops + " days=" + entry.days
          + " rank_sum=" + entry.rankSum);
    }
  }
  if (this._c48PassLedger != null && ("pass" in this._c48PassLedger)) {
    local entry = this._c48PassLedger.pass;
    OpexC48ProjectAttemptLog("phase=annual_pass year=" + year + " passes=" + entry.passes
        + " attempts_total=" + entry.attemptsTotal + " ops_total=" + entry.opsTotal
        + " built=" + entry.built + " best_len_sum=" + entry.bestLenSum
        + " max_rank_sum=" + entry.maxRankSum);
  }
  this._c48AttemptLedger = {};
  this._c48PassLedger = {};
}

/* C49 : une seule cause, pour le premier rang non bati de LA passe. La tresorerie est lue ici,
 * a la fin : la question est MARGINALE — « given what we just did, what blocked the next one? ».
 * Une construction qui a consomme du cash rend donc correctement le rang suivant bloque par
 * TRESORERIE. Un projet non tente ne peut pas etre teste sur la carte sans changer la decision
 * et consommer des opcodes : `site` n'est attribue qu'a un echec carte deja observe ; `decision`
 * absorbe ces echecs carte non observes. C'est une limite acceptee, pas une omission. */
function OpexAI::_recordC49ScarcityPass(best, builtRanks, attemptedRanks, passDiscards)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  this._c49ScarcityLedger.passes++;
  if (best == null || best.len() == 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local targetRank = -1;
  for (local i = 0; i < best.len(); i++) {
    if (!(i in builtRanks)) {
      targetRank = i;
      break;
    }
  }
  if (targetRank < 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local project = best[targetRank];
  if (project == null) {
    this._c49ScarcityLedger.none++;
    return;
  }
  local available = OpexAvailableCapital();
  if (project.capital > available) {
    this._c49ScarcityLedger.cash++;
    return;
  }

  local vehicleType = OpexC49VehicleType(project.mode);
  local vehicleMode = project.mode == "fleet" ? "air" : project.mode;
  local setting = OpexTensionVehicleSetting(vehicleMode);
  if (vehicleType >= 0 && setting != null && AIGameSettings.IsValid(setting)) {
    local planned = OpexTensionProjectVehicleCount(project);
    local cap = AIGameSettings.GetValue(setting);
    if (AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, vehicleType) + planned > cap) {
      this._c49ScarcityLedger.vehicles++;
      return;
    }
  }

  if (OpexC49IsMapFailure(passDiscards, targetRank)) {
    this._c49ScarcityLedger.site++;
    return;
  }
  if (targetRank in attemptedRanks) this._c49ScarcityLedger.decision_attempted++;
  else this._c49ScarcityLedger.decision_unattempted++;
}

/* La tache report publie au premier passage de l'annee suivante : year=1971 decrit donc 1970,
 * et la derniere annee de partie n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexAI::_logC49ScarcityLedger(year)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  local entry = this._c49ScarcityLedger;
  local regime = this._c49ScarcityRegime;
  local best = entry.cash;
  local decision = entry.decision_attempted + entry.decision_unattempted;
  foreach (resource in ["vehicles", "site"]) {
    if (entry[resource] > best) best = entry[resource];
  }
  if (decision > best) best = decision;
  local leaders = 0;
  foreach (resource in ["cash", "vehicles", "site"]) {
    if (entry[resource] == best) leaders++;
  }
  if (decision == best) leaders++;
  if (leaders == 1) {
    foreach (resource in ["cash", "vehicles", "site"]) {
      if (entry[resource] == best) {
        regime = resource;
        break;
      }
    }
    if (decision == best) regime = "decision";
  }
  /* Egalite : ne pas remplacer le regime precedent, hysteresis sans constante. */
  this._c49ScarcityRegime = regime;
  OpexC49ScarcityLog("phase=annual year=" + year + " passes=" + entry.passes
      + " cash=" + entry.cash + " vehicles=" + entry.vehicles + " site=" + entry.site
      + " decision_attempted=" + entry.decision_attempted
      + " decision_unattempted=" + entry.decision_unattempted
      + " none=" + entry.none + " regime=" + regime);
  this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
      decision_attempted = 0, decision_unattempted = 0, none = 0 };
}

/* C55 : le report de debut d'annee publie l'annee ecoulee. La ligne summary est cumulative ;
 * la derniere ligne du log est donc aussi la synthese de fin de partie lisible sans jointure. */
function OpexAI::_logC55OriginRelaxLedger(year)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  local entry = C55_ORIGIN_RELAX_LEDGER;
  OpexC55OriginRelaxLog("phase=annual year=" + year + " candidates_seen=" + entry.candidates_seen
      + " rejected_total=" + entry.rejected_total + " both_served=" + entry.both_served
      + " one_served=" + entry.one_served + " one_served_pax=" + entry.one_served_pax
      + " one_served_freight=" + entry.one_served_freight
      + " duplicate_exact=" + entry.duplicate_exact);
  entry.total_candidates_seen += entry.candidates_seen;
  entry.total_rejected_total += entry.rejected_total;
  entry.total_both_served += entry.both_served;
  entry.total_one_served += entry.one_served;
  entry.total_one_served_pax += entry.one_served_pax;
  entry.total_one_served_freight += entry.one_served_freight;
  entry.total_duplicate_exact += entry.duplicate_exact;
  OpexC55OriginRelaxLog("phase=summary year=" + year + " candidates_seen=" + entry.total_candidates_seen
      + " rejected_total=" + entry.total_rejected_total + " both_served=" + entry.total_both_served
      + " one_served=" + entry.total_one_served + " one_served_pax=" + entry.total_one_served_pax
      + " one_served_freight=" + entry.total_one_served_freight
      + " duplicate_exact=" + entry.total_duplicate_exact);
  C55_ORIGIN_RELAX_LEDGER = {
    candidates_seen = 0, rejected_total = 0, both_served = 0, one_served = 0,
    one_served_pax = 0, one_served_freight = 0, duplicate_exact = 0,
    total_candidates_seen = entry.total_candidates_seen, total_rejected_total = entry.total_rejected_total,
    total_both_served = entry.total_both_served, total_one_served = entry.total_one_served,
    total_one_served_pax = entry.total_one_served_pax,
    total_one_served_freight = entry.total_one_served_freight,
    total_duplicate_exact = entry.total_duplicate_exact,
  };
}

/* La tache "report" publie au premier passage de l'annee suivante : year=1971 decrit donc
 * l'annee de jeu 1970, et la derniere annee de la partie n'est jamais publiee. Tous les appels
 * API couteux sont apres ce garde C54, afin que le defaut false n'atteigne aucune API ajoutee. */
function OpexAI::_logC54VehicleOrders(year)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local vehicles = AIVehicleList();
  foreach (vehicle, _ in vehicles) {
    local vehicleType = AIVehicle.GetVehicleType(vehicle);
    local mode = vehicleType == AIVehicle.VT_RAIL ? "rail"
        : vehicleType == AIVehicle.VT_ROAD ? "road"
        : vehicleType == AIVehicle.VT_AIR ? "air"
        : vehicleType == AIVehicle.VT_WATER ? "water" : "invalid";
    local orders = AIOrder.GetOrderCount(vehicle);
    local destinations = {};
    for (local position = 0; position < orders; position++) {
      /* IsGotoStationOrder exclut depot, waypoint et conditionnel avant GetOrderDestination. */
      if (!AIOrder.IsGotoStationOrder(vehicle, position)) continue;
      local destination = AIOrder.GetOrderDestination(vehicle, position);
      destinations.rawset(destination, true);
    }
    local line = OpexC41PersistedLineForVehicle(this._lines, vehicle);
    local lineId = line != null && ("lineId" in line) ? line.lineId : -1;
    /* GetProfit* est en livres reelles via API, contrairement a VEHS (~256 x livres). */
    OpexC54VehicleOrdersLog("phase=vehicle year=" + year + " vid=" + vehicle
        + " mode=" + mode + " engine=" + AIVehicle.GetEngineType(vehicle)
        + " age=" + AIVehicle.GetAge(vehicle) + " max_age=" + AIVehicle.GetMaxAge(vehicle)
        + " orders=" + orders + " distinct_dest=" + destinations.len()
        + " profit_last=" + AIVehicle.GetProfitLastYear(vehicle)
        + " profit_this=" + AIVehicle.GetProfitThisYear(vehicle)
        + " in_depot=" + (AIVehicle.IsStoppedInDepot(vehicle) ? 1 : 0)
        + " line=" + lineId);
  }
}

/* C48.1 : tous les compteurs de volume sont explicites dans chaque ligne :
 * lines = lines.len() a l'entree (total), groups/projects_scanned/retained = rejeu des groupes,
 * fresh_feeders = feeders produits, fleet_plan = elements lus, air_plans = plans produits,
 * alternatives/selected = entree/sortie de la selection. Les champs non pertinents a une phase
 * valent zero. La tache report publie au premier passage de l'annee suivante : year=1971 decrit
 * 1970 et la derniere annee n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexC48IncrementalRecord(step, ops, days, lines, groups, projectsScanned, retained,
                                  freshFeeders, fleetPlan, airPlans, alternatives, selected)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  if (C48_INCREMENTAL_LEDGER == null) C48_INCREMENTAL_LEDGER = {};
  local entry = (step in C48_INCREMENTAL_LEDGER) ? C48_INCREMENTAL_LEDGER[step]
      : { calls = 0, ops = 0, days = 0, lines = 0, groups = 0, projectsScanned = 0,
          retained = 0, freshFeeders = 0, fleetPlan = 0, airPlans = 0, alternatives = 0,
          selected = 0 };
  entry.calls++;
  entry.ops += ops;
  entry.days += days;
  entry.lines += lines;
  entry.groups += groups;
  entry.projectsScanned += projectsScanned;
  entry.retained += retained;
  entry.freshFeeders += freshFeeders;
  entry.fleetPlan += fleetPlan;
  entry.airPlans += airPlans;
  entry.alternatives += alternatives;
  entry.selected += selected;
  C48_INCREMENTAL_LEDGER.rawset(step, entry);
}

function OpexAI::_logC48IncrementalLedger(year)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  /* Une ligne pour CHACUNE des sept phases, meme si une garde fonctionnelle n'a produit aucun
   * appel cette annee : le depouillement distingue ainsi zero de "phase absente du journal". */
  local steps = ["tension_ctx", "groups_replay", "feeders", "fleet", "air", "selection", "total"];
  foreach (step in steps) {
    local entry = (C48_INCREMENTAL_LEDGER != null && (step in C48_INCREMENTAL_LEDGER))
        ? C48_INCREMENTAL_LEDGER[step]
        : { calls = 0, ops = 0, days = 0, lines = 0, groups = 0, projectsScanned = 0,
            retained = 0, freshFeeders = 0, fleetPlan = 0, airPlans = 0, alternatives = 0,
            selected = 0 };
    OpexC48IncrementalLog("phase=annual year=" + year + " step=" + step
        + " calls=" + entry.calls + " ops=" + entry.ops + " days=" + entry.days
        + " lines=" + entry.lines + " groups=" + entry.groups
        + " projects_scanned=" + entry.projectsScanned + " retained=" + entry.retained
        + " fresh_feeders=" + entry.freshFeeders + " fleet_plan=" + entry.fleetPlan
        + " air_plans=" + entry.airPlans + " alternatives=" + entry.alternatives
        + " selected=" + entry.selected);
  }
  C48_INCREMENTAL_LEDGER = null;
}

/* File CONTINUE : le scan reprend apres la derniere tache choisie, meme si un A* a franchi le
 * changement d'annee. Le calendrier ne decide plus RIEN : quand le suffixe de la table est fini,
 * _taskCycle avance et le scan repart a zero. Chaque tache se reporte par dueCycle, donc aucun
 * item ne peut affamer ceux places apres lui et le dernier rend litteralement la main au premier. */
function OpexAI::_runNextTask()
{
  if (C41_SLACK_LEDGER || C41_MONTHLY_BUSY_LEDGER || C41_OPPORTUNITY_LEDGER || C41_ADMISSION_LEDGER || C39_PASS_CLOCK_LEDGER) this._c41LastTaskName = "idle";
  /* C41.46 : sentinelle -1 = aucune tranche A* mesuree cette passe. Remise a chaque passage,
   * lue par _runNextTaskWithSlackLedger juste apres le retour de cette fonction. */
  if (C41_RAIL_SLICE_LEDGER) this._c41RailSliceLastOps = -1;
  /* C39.6 : meme patron, scratch INDEPENDANT des champs _c41RailSliceLast* ci-dessus. */
  if (C39_PASS_CLOCK_LEDGER) {
    this._c39PassClockSliceDays = -1;
    this._c39PassClockSliceTicks = -1;
    this._c39PassClockSliceOps = -1;
  }
  if (DECISION_LOG) {
    _currentTaskName = null;
    _currentTaskLogged = false;
  }
  if (this._taskQueue == null || this._taskQueue.len() == 0) return false;
  /* Sonder d'abord la transaction, puis CONTINUER la file dans le meme passage. Retourner ici
   * affamait de nouveau le scheduler pendant tout le trajet vers le depot (jusqu'a un an mesure),
   * alors que ce trajet ne consomme aucun opcode de l'IA. */
  if (this._railExpansion != null) this._continueRailExpansion();
  /* A4 : avancer l'A* d'une tranche PUIS continuer la file, comme _railExpansion. Retourner
   * ici sans encherner les autres taches reconstituerait le gel (rien d'autre ne tourne tant
   * que la recherche n'a pas fini). */
  if (this._railSearch != null) {
    /* C41.46 : n'encadrer que les passes qui font REELLEMENT avancer l'A* -- phase == "search".
     * phase == "build" retourne immediatement pour kind == "primary" (le cout reel est ailleurs,
     * dans _consumeRailSearch via la tache "projects") ou execute _consumeRailUpgrade() pour
     * kind == "upgrade", qui n'est pas une tranche de recherche. Aucun des deux n'est comptabilise
     * dans ce ledger : le confondre fausserait "iterations cumulees" et "tranches non terminees". */
    if ((C41_RAIL_SLICE_LEDGER || C39_PASS_CLOCK_LEDGER) && this._railSearch.phase == "search") {
      local sliceState = this._railSearch;
      local spentBefore = sliceState.spent;
      /* C39.6 : date/tick AVANT l'appel, pour le delta de la SEULE tranche. sliceMark.tick sert
       * de tick de depart -- pas de second AIController.GetTick(). */
      local c39SliceDateBefore = C39_PASS_CLOCK_LEDGER ? AIDate.GetCurrentDate() : -1;
      local sliceMark = OpexOpsMeasureBegin();
      this._continueRailSearch();
      /* C39.6 reutilise ce MEME sliceOps que C41.46 -- pas de second begin()/end() pour la meme
       * tranche, les deux sondes partagent la seule mesure d'opcodes necessaire. */
      local sliceOps = OpexOpsMeasureEnd(sliceMark);
      if (C41_RAIL_SLICE_LEDGER) {
        this._c41RailSliceLastOps = sliceOps;
        this._c41RailSliceLastIterDelta = sliceState.spent - spentBefore;
        /* sliceState reste la MEME table (mutee en place par _continueRailSearch) : phase !=
         * "search" signifie que cette tranche a atteint slice.done et fait basculer la recherche
         * en "build". */
        this._c41RailSliceLastDone = (sliceState.phase != "search");
      }
      if (C39_PASS_CLOCK_LEDGER) {
        this._c39PassClockSliceDays = AIDate.GetCurrentDate() - c39SliceDateBefore;
        this._c39PassClockSliceTicks = AIController.GetTick() - sliceMark.tick;
        this._c39PassClockSliceOps = sliceOps;
      }
    } else {
      this._continueRailSearch();
    }
  }
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local task = null;
  local taskIndex = -1;
  for (local index = this._taskCursor; index < this._taskQueue.len(); index++) {
    local candidate = this._taskQueue[index];
    if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
      task = candidate;
      taskIndex = index;
      break;
    }
  }
  if (task == null) {
    this._taskCycle++;
    this._taskCursor = 0;
    for (local index = 0; index < this._taskQueue.len(); index++) {
      local candidate = this._taskQueue[index];
      if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
        task = candidate;
        taskIndex = index;
        break;
      }
    }
  }
  if (task == null) return false;
  this._taskCursor = (taskIndex + 1) % this._taskQueue.len();
  if (C41_SLACK_LEDGER || C41_MONTHLY_BUSY_LEDGER || C41_OPPORTUNITY_LEDGER || C41_ADMISSION_LEDGER || C39_PASS_CLOCK_LEDGER) this._c41LastTaskName = task.name;

  /* Defaut : exactement une execution par tour continu. Une tache inutile peut choisir plus loin. */
  task.dueCycle = this._taskCycle + 1;
  if (DECISION_LOG) {
    _currentTaskName = task.name;
    _currentTaskLogged = false;
  }

  if (task.name == "catalog") {
    local date = AIDate.GetCurrentDate();
    local ym = year * 12 + AIDate.GetMonth(date);
    /* portfolio_v2 : le portefeuille n'etait regenere qu'au CHANGEMENT DE MOIS ou apres une
     * construction reussie, et son capitalBudget etait fige a la generation. Un mois qui s'ouvrait
     * a 60 k£ sans projet finançable rendait donc un portefeuille vide, et _tryBuildProjects
     * sortait des sa premiere ligne POUR TOUT LE MOIS -- meme si la tresorerie montait ensuite a
     * 400 k£. C'est la mesure « 4,15 mois en moyenne avec >= 100 k£ et aucune croissance »
     * (docs/taches.md S0 septies, trouvaille A). On regenere donc aussi des que le capital
     * mobilisable a materiellement grandi depuis la derniere generation. */
    local stale = false;
    if (PORTFOLIO_V2 && this._projects != null) {
      local budgetNow = OpexAvailableCapital();
      local budgetThen = this._projects.capitalBudget;
      /* Seuil relatif ET absolu : on ne rejoue pas la generation pour quelques milliers de livres,
       * mais un doublement du capital mobilisable rouvre le vivier. */
      local gainOk = budgetNow > budgetThen + PORTFOLIO_REFRESH_MIN_GAIN;
      local doubleOk = budgetNow > budgetThen * 2;
      if (PORTFOLIO_REFRESH_PROBE) {
        PORTFOLIO_REFRESH_PROBE_CHECKS++;
        if (gainOk) PORTFOLIO_REFRESH_PROBE_GAIN_OK++;
        if (doubleOk) PORTFOLIO_REFRESH_PROBE_DOUBLE_OK++;
        /* C43/E3 : le seul cas ou PORTFOLIO_REFRESH_MIN_GAIN bloque reellement un rafraichissement
         * que le doublement aurait seul autorise -- utile seulement si budgetThen < MIN_GAIN. */
        if (doubleOk && !gainOk) PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY++;
      }
      if (gainOk && doubleOk) stale = true;
    }
    /* Une invalidation evenementielle prime toujours la cadence mensuelle et le seuil de
     * tresorerie : le portefeuille est derive du catalogue, pas seulement du capital. */
    if (this._lastCatalogMonth == ym && this._projects != null && !stale &&
        !this._portfolioInvalidated) return false;
    local refreshReason = this._portfolioInvalidated ? "event"
        : (stale ? "capital" : "month");
    if (DECISION_LOG) {
      OpexDecide("PORTFOLIO_REFRESH", "reason=" + refreshReason + " budget="
                 + OpexAvailableCapital());
    }
    this._lastCatalogMonth = ym;
    this._pruneAbandonedPairs(date);
    if (PORTFOLIO_REFRESH_PROBE) {
      local refreshMark = OpexOpsMeasureBegin();
      this._catalog.refresh(this._budget, year);
      PORTFOLIO_REFRESH_PROBE_REFRESH_OPS += OpexOpsMeasureEnd(refreshMark);
      PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT++;
    } else {
      this._catalog.refresh(this._budget, year);
    }
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (this._recomputeEpochBounds) {
      OpexRefreshEpochBounds(this._catalog);
      this._recomputeEpochBounds = false;
    }
    this._rebuildProjects(fleetPlan);
    /* C39.5 : le vivier vient d'etre (re)genere. Horodater ici, et pas seulement au prochain
     * tour projects, pour que D2 mesure toute la fenetre de finançabilite. */
    if (C39_PROJECTS_CADENCE_PROBE) this._c39StampFinanceable();
    if (this._catalog != null && this._catalog.bounds != null) {
      local b = this._catalog.bounds;
      OpexSign(AIMap.GetTileIndex(1, 2), "EB|" + b.roadMin + "|" + b.railMin
               + "|" + b.railAirOverlapMin + "|" + b.railMax);
    }
    if ((C41_ROAD_CANDIDATE_PROFILE || C41_ROAD_FREIGHT_PROFILE || C41_ROAD_FREIGHT_TOWN_PROFILE || C41_ROAD_FEEDER_PROFILE) && this._projects != null && ("road" in this._projects) &&
        this._projects.road != null && ("profile" in this._projects.road) &&
        this._projects.road.profile != null) {
      local profile = this._projects.road.profile;
      if (C41_ROAD_CANDIDATE_PROFILE) {
        OpexC39Log("C41_ROAD_CANDIDATE_PROFILE", "ops=" + this._projects.road.opcodes
                   + " pax_ops=" + profile.paxOps + " freight_ops=" + profile.freightOps
                   + " feeder_ops=" + profile.feederOps + " topk_ops=" + profile.topKOps
                   + " candidates=" + this._projects.road.all);
      }
      if (C41_ROAD_FREIGHT_PROFILE) {
        OpexC39Log("C41_ROAD_FREIGHT_PROFILE", "road_ops=" + this._projects.road.opcodes
                   + " preparation_ops=" + profile.freightPreparationOps
                   + " industry_ops=" + profile.freightIndustryOps
                   + " town_ops=" + profile.freightTownOps
                   + " candidates=" + this._projects.road.all);
      }
      if (C41_ROAD_FREIGHT_TOWN_PROFILE) {
        OpexC39Log("C41_ROAD_FREIGHT_TOWN_PROFILE", "road_ops=" + this._projects.road.opcodes
                   + " scanned=" + profile.freightTownScanned
                   + " acceptance_hits=" + profile.freightTownAcceptanceHits
                   + " acceptance_misses=" + profile.freightTownAcceptanceMisses
                   + " acceptance_ops=" + profile.freightTownAcceptanceOps
                   + " accepted_pairs=" + profile.freightTownAcceptedPairs
                   + " candidate_ops=" + profile.freightTownCandidateOps);
      }
      if (C41_ROAD_FEEDER_PROFILE) {
        OpexC39Log("C41_ROAD_FEEDER_PROFILE", "build_ops=" + profile.feederOps);
      }
    }
    if (C41_RAIL_PORTFOLIO_PROFILE && this._projects != null && ("stats" in this._projects)
        && this._projects.stats != null && ("railProfile" in this._projects.stats)) {
      local railProfile = this._projects.stats.railProfile;
      OpexC39Log("C41_RAIL_PORTFOLIO_PROFILE", "generation_ops=" + railProfile.generationOps
                 + " generation_candidates=" + railProfile.generationCandidates
                 + " topk_candidates=" + railProfile.topKCandidates
                 + " prequote_ops=" + railProfile.prequoteOps
                 + " prequote_attempted=" + railProfile.prequoteAttempted
                 + " prequote_quoted=" + railProfile.prequoteQuoted
                 + " prequote_failed=" + railProfile.prequoteFailed
                 + " insert_ops=" + railProfile.insertOps
                 + " inserted_projects=" + railProfile.insertedProjects
                 + " selection_ops=" + this._projects.stats.selectionOpcodes
                 + " selection_considered=" + this._projects.stats.budgetConsidered
                 + " selection_selected=" + this._projects.stats.budgetSelected);
    }
    if (C41_RAIL_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_CANDIDATE_PROFILE", "ops=" + this._projects.rail.opcodes
                 + " pax_ops=" + profile.paxOps + " freight_ops=" + profile.freightOps
                 + " topk_ops=" + profile.topKOps + " candidates=" + this._projects.rail.all);
    }
    if (C41_RAIL_PAX_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_PROFILE", "preparation_ops=" + profile.paxPreparationOps
                 + " pair_total_ops=" + profile.paxPairTotalOps
                 + " candidate_ops=" + profile.paxCandidateOps
                 + " pairs_scanned=" + profile.paxPairsScanned
                 + " candidate_calls=" + profile.paxCandidateCalls
                 + " candidates=" + this._projects.rail.all);
    }
    if (C41_RAIL_PAX_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_CANDIDATE_PROFILE", "sitable_ops=" + profile.paxSitableOps
                 + " sitable_calls=" + profile.paxSitableCalls
                 + " economics_ops=" + profile.paxEconomicsOps
                 + " economics_calls=" + profile.paxEconomicsCalls);
    }
    if (C41_RAIL_PAX_ECONOMICS_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_ECONOMICS_PROFILE", "total_ops=" + profile.paxEconomicsOps
                 + " calls=" + profile.paxEconomicsCalls
                 + " setup_ops=" + profile.paxEconomicsSetupOps
                 + " loop_ops=" + profile.paxEconomicsLoopOps
                 + " loop_calls=" + profile.paxEconomicsLoopCalls
                 + " post_ops=" + profile.paxEconomicsPostOps);
    }
    if (C41_RAIL_PAX_SPEED_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_SPEED_PROFILE", "setup_ops=" + profile.paxEconomicsSetupOps
                 + " speed_ops=" + profile.paxSpeedOps
                 + " speed_calls=" + profile.paxSpeedCalls
                 + " corrected_speed_calls=" + profile.paxCorrectedSpeedCalls);
    }
    if (C41_RAIL_PAX_SPEED_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_SPEED_DETAIL_PROFILE", "cruise_ops=" + profile.paxCruiseOps
                 + " acceleration_ops=" + profile.paxAccelerationOps
                 + " integration_ops=" + profile.paxIntegrationOps
                 + " speed_calls=" + profile.paxSpeedCalls
                 + " unique_keys=" + profile.paxSpeedUniqueKeys
                 + " cacheable_hits=" + profile.paxSpeedCacheableHits);
    }
    if (C41_RAIL_PAX_CRUISE_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_PAX_CRUISE_PROFILE", "cruise_ops=" + profile.paxCruiseOps
                 + " cruise_calls=" + profile.paxCruiseCalls
                 + " unique_keys=" + profile.paxCruiseUniqueKeys
                 + " cacheable_hits=" + profile.paxCruiseCacheableHits);
    }
    if (C41_RAIL_FREIGHT_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_PROFILE", "preparation_ops=" + profile.freightPreparationOps
                 + " industry_ops=" + profile.freightIndustryOps
                 + " town_ops=" + profile.freightTownOps);
    }
    if (C41_RAIL_FREIGHT_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_CANDIDATE_PROFILE", "industry_ops=" + profile.freightIndustryOps
                 + " industry_candidate_ops=" + profile.freightIndustryCandidateOps
                 + " industry_candidate_calls=" + profile.freightIndustryCandidateCalls
                 + " town_ops=" + profile.freightTownOps
                 + " town_candidate_ops=" + profile.freightTownCandidateOps
                 + " town_candidate_calls=" + profile.freightTownCandidateCalls);
    }
    if (C41_RAIL_FREIGHT_ECONOMICS_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail)
        && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_PROFILE", "ops=" + profile.freightEconomicsOps
                 + " calls=" + profile.freightEconomicsCalls);
    }
    if (C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE", "ops=" + profile.freightEconomicsOps
                 + " calls=" + profile.freightEconomicsCalls
                 + " setup_ops=" + profile.freightEconomicsSetupOps
                 + " setup_calls=" + profile.freightEconomicsSetupCalls
                 + " loop_ops=" + profile.freightEconomicsLoopOps
                 + " loop_calls=" + profile.freightEconomicsLoopCalls
                 + " post_ops=" + profile.freightEconomicsPostOps
                 + " post_calls=" + profile.freightEconomicsPostCalls);
    }
    if (C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE", "ops=" + profile.freightEconomicsOps
                 + " calls=" + profile.freightEconomicsCalls
                 + " reference_ops=" + profile.freightEconomicsReferenceOps
                 + " reference_calls=" + profile.freightEconomicsReferenceCalls
                 + " consist_ops=" + profile.freightEconomicsConsistOps
                 + " consist_calls=" + profile.freightEconomicsConsistCalls
                 + " capital_ops=" + profile.freightEconomicsCapitalOps
                 + " capital_calls=" + profile.freightEconomicsCapitalCalls);
    }
    if (C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE", "ops=" + profile.freightEconomicsOps
                 + " initial_speed_ops=" + profile.freightEconomicsConsistInitialSpeedOps
                 + " initial_speed_calls=" + profile.freightEconomicsConsistInitialSpeedCalls
                 + " corrected_speed_ops=" + profile.freightEconomicsConsistCorrectedSpeedOps
                 + " corrected_speed_calls=" + profile.freightEconomicsConsistCorrectedSpeedCalls);
    }
    if (C41_RAIL_FREIGHT_CRUISE_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_CRUISE_PROFILE", "cruise_calls=" + profile.freightCruiseCalls
                 + " unique_keys=" + profile.freightCruiseUniqueKeys
                 + " cacheable_hits=" + profile.freightCruiseCacheableHits);
    }
    if (C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE", "acceleration_ops=" + profile.freightAccelerationOps
                 + " acceleration_calls=" + profile.freightAccelerationCalls
                 + " integration_ops=" + profile.freightIntegrationOps
                 + " integration_calls=" + profile.freightIntegrationCalls);
    }
    if (C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE", "calls=" + profile.freightSpeedCalls
                 + " unique_keys=" + profile.freightSpeedUniqueKeys + " cacheable_hits=" + profile.freightSpeedCacheableHits);
    }
    if (C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE && this._projects != null && ("rail" in this._projects)
        && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
      local profile = this._projects.rail.profile;
      OpexC39Log("C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE", "ops=" + profile.freightTownGuardsOps + " calls=" + profile.freightTownGuardsCalls + " service_ops=" + profile.freightTownServiceOps + " service_calls=" + profile.freightTownServiceCalls);
    }
    this._logStalenessRefresh(refreshReason);
    this._portfolioInvalidated = false;
    this._ranked = this._projects.rail;
    if (PORTFOLIO_LOG) {
      if (this._projects != null && this._projects.best != null && this._projects.best.len() > 0) {
        OpexLogPortfolioRank(this._projects);
      } else if (DECISION_LOG) {
        local cBudget = (this._projects != null) ? this._projects.capitalBudget : 0;
        OpexDecide("PORTFOLIO_EMPTY", "budget=" + cBudget);
      }
    }
    local anchor = AIMap.GetTileIndex(1, 1);
    local yy = year % 100;
    /* `knapsackExact` et le compteur d'imbrications du budget etaient ECRITS ET LUS NULLE PART.
     * Or maxNodes = 2000 pour n = 64 fait tronquer la recherche couramment : sans ce champ, on ne
     * peut pas distinguer « le solveur a prouve l'optimum » de « il a epuise son budget de noeuds »
     * -- l'angle mort qui a laisse survivre quatre defauts du portefeuille (docs/taches.md
     * S0 septies). Ajoutes au panneau EXISTANT plutot que dans un nouveau : un appel BuildSign de
     * plus deplace les frontieres de ticks (precedent mesure : un helper devant 57 appels a coute
     * 3 lignes rail). Longueur maximale d'un panneau : 31 caracteres. */
    OpexSign(anchor, "IG|" + yy + "|" + this._projects.stats.modeCandidates + "|"
             + this._projects.stats.odProjects + "|" + this._projects.stats.budgetSelected
             + "|" + (this._projects.stats.knapsackExact ? 0 : 1)
             + "|" + this._budget.nested);
    /* air_fleet_probe : combien de hubs le rabattage voit-il, et combien de candidats feeders
     * en tire-t-il ? Sans ces deux nombres, un "zero feeder bati" ne dit pas si la generation
     * est vide ou si l'election les ecarte. */
    if (AIR_FLEET_PROBE && ("road" in this._projects) && ("stats" in this._projects.road) &&
        ("feederCandidates" in this._projects.road.stats)) {
      OpexSign(anchor, "FN|" + yy + "|" + this._projects.road.stats.feederHubs
                             + "|" + this._projects.road.stats.feederCandidates);
    }
    OpexSign(anchor, "IB|" + yy + "|" + this._projects.capitalBudget + "|"
             + this._projects.stats.selectedCapital);
    return true;
  }
  if (task.name == "c41_water") {
    /* C41.1 : aucun merge de candidats ni re-election n'est encore correct. La tache consomme
     * exclusivement la revision qu'elle a vraiment reconstruite. */
    task.dueCycle = 2147483647;
    if (!C41_WATER_REFRESH || !C41_REVISION_PROBE || this._staleness == null ||
        this._staleness.revisions.catalog.water <= this._staleness.acknowledged.catalog.water) {
      return false;
    }
    local revision = this._staleness.revisions.catalog.water;
    /* Le slack est seulement le reliquat du tick d'admission. Si la tache traverse un tick,
     * ses opcodes ulterieurs sont comptabilises dans `ops`, jamais abuses comme slack initial. */
    local slackOpsAvailable = AIController.GetOpsTillSuspend();
    local ops = this._catalog.refreshWater(this._budget);
    local stalenessAgeDays = this._staleness.waterCatalogDirtyDate >= 0
        ? AIDate.GetCurrentDate() - this._staleness.waterCatalogDirtyDate : -1;
    this._staleness.acknowledged.catalog.water = revision;
    this._staleness.catalog.water = false;
    OpexC39Log("C41_WATER_REFRESH", "revision=" + revision + " ops=" + ops
               + " ships=" + this._catalog.ships.len()
               + " staleness_age_days=" + stalenessAgeDays
               + " slack_ops_available=" + slackOpsAvailable
               + " slack_ops_used=" + (ops < slackOpsAvailable ? ops : slackOpsAvailable));
    if (C41_STALENESS_LEDGER) {
      OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog.water method=targeted revision="
                          + revision + " age_days=" + stalenessAgeDays);
    }
    this._staleness.waterCatalogDirtyDate = -1;
    this._staleness.waterCatalogDirtyTick = -1;
    this._staleness.dirtySince.catalog.water = -1;
    /* C41.3 : OpexWaterPlans travaille dans un tableau temporaire. Ses tests de docks sont sous
     * AITestMode ; aucun projet persistant ni revision aval n'est modifie dans cette tranche.
     * Le catalogue geometrique eau est la seule memoisation voulue : un moteur nouveau ne doit
     * pas relancer le scan du littoral. */
    if (C41_WATER_CANDIDATE_PROBE) {
      local plans = [];
      local profile = C41_WATER_PLANS_PROFILE ? {
        town_sort_ops = 0, site_ops = 0, pair_total_ops = 0, pair_filter_rank_ops = 0,
        bfs_ops = 0, economics_ops = 0, towns_considered = 0, sites_found = 0,
        pairs_considered = 0, pairs_after_range = 0, bfs_attempts = 0,
        bfs_connected = 0, economics_attempts = 0, positive_economics = 0,
        dock_test_ops = 0, site_scan_filter_ops = 0, coast_candidates = 0,
        navigable_coast_candidates = 0, dock_tests = 0, site_cache_hits = 0,
        site_cache_misses = 0, site_tiles_visited = 0,
      } : null;
      this._budget.begin();
      OpexWaterPlans(this._catalog, this._lines, plans, profile, this._waterSiteCatalog);
      local planOps = this._budget.end("project_water_targeted_probe");
      OpexC39Log("C41_WATER_PLANS", "revision=" + revision + " ops=" + planOps
                 + " plans=" + plans.len());
      if (profile != null) {
        OpexC39Log("C41_WATER_PLAN_PROFILE", "revision=" + revision + " ops=" + planOps
                   + " slack_ops_available=" + slackOpsAvailable
                   + " slack_ops_used=" + ((ops + planOps) < slackOpsAvailable
                                             ? (ops + planOps) : slackOpsAvailable)
                   + " town_sort_ops=" + profile.town_sort_ops + " site_ops=" + profile.site_ops
                   + " pair_total_ops=" + profile.pair_total_ops
                   + " pair_filter_rank_ops=" + profile.pair_filter_rank_ops
                   + " bfs_ops=" + profile.bfs_ops + " economics_ops=" + profile.economics_ops
                   + " towns=" + profile.towns_considered + " sites=" + profile.sites_found
                   + " pairs=" + profile.pairs_considered + " range=" + profile.pairs_after_range
                   + " bfs=" + profile.bfs_attempts + " connected=" + profile.bfs_connected
                   + " economics=" + profile.economics_attempts
                   + " positive=" + profile.positive_economics
                   + " dock_test_ops=" + profile.dock_test_ops
                   + " site_scan_filter_ops=" + profile.site_scan_filter_ops
                   + " coast=" + profile.coast_candidates
                   + " navigable_coast=" + profile.navigable_coast_candidates
                   + " dock_tests=" + profile.dock_tests
                   + " site_cache_hits=" + profile.site_cache_hits
                   + " site_cache_misses=" + profile.site_cache_misses
                   + " site_tiles_visited=" + profile.site_tiles_visited);
      }
    }
    return true;
  }
  if (task.name == "c41_road") {
    /* C41.15 : un seul acquittement, sans candidats/portefeuille/re-election. */
    task.dueCycle = 2147483647;
    if (!C41_ROAD_REFRESH || !C41_REVISION_PROBE || this._staleness == null ||
        this._staleness.revisions.catalog.road <= this._staleness.acknowledged.catalog.road) {
      return false;
    }
    local revision = this._staleness.revisions.catalog.road;
    local slackOpsAvailable = AIController.GetOpsTillSuspend();
    local ops = this._catalog.refreshRoad(this._budget);
    local stalenessAgeDays = this._staleness.dirtySince.catalog.road >= 0
        ? AIDate.GetCurrentDate() - this._staleness.dirtySince.catalog.road : -1;
    this._staleness.acknowledged.catalog.road = revision;
    this._staleness.catalog.road = false;
    OpexC39Log("C41_ROAD_REFRESH", "revision=" + revision + " ops=" + ops
               + " cargo_engines=" + this._catalog.roadEngineByCargo.len()
               + " staleness_age_days=" + stalenessAgeDays
               + " slack_ops_available=" + slackOpsAvailable
               + " slack_ops_used=" + (ops < slackOpsAvailable ? ops : slackOpsAvailable));
    if (C41_STALENESS_LEDGER) {
      OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog.road method=targeted revision="
                          + revision + " age_days=" + stalenessAgeDays);
    }
    this._staleness.dirtySince.catalog.road = -1;
    return true;
  }
  if (this._projects == null) {
    /* `_taskCycle` (et non `+ 1`) laissait la tache due au cycle COURANT. Or le cycle n'avance que
     * lorsque le balayage depuis _taskCursor ne trouve plus rien de du : une tache qui reste
     * eternellement due empeche donc `_taskCycle` d'avancer, et `catalog` -- differe a
     * `_taskCycle + 1` -- ne tourne plus JAMAIS. L'IA tournerait alors a vide pour le reste de la
     * partie avec `_projects` null a jamais. Inatteignable aujourd'hui puisque OpexBuildProjects
     * ne rend jamais null, mais un seul `return` ajoute la-bas gelait l'IA (docs/taches.md
     * S0 sexies). */
    task.dueCycle = this._taskCycle + 1;
    return false;
  }
  if (task.name == "c41_rail_signals") {
    task.dueCycle = 2147483647;
    if (!C41_RAIL_LOST_SIGNAL_REPAIR || this._c41RailSignalLines == null) return false;
    local lineId = -1;
    foreach (pendingLine, ignored in this._c41RailSignalLines) { lineId = pendingLine.tointeger(); break; }
    if (lineId < 0) { task.enabled = false; return false; }
    delete this._c41RailSignalLines["" + lineId];
    local line = this._findLineById(lineId);
    if (line == null || !("mode" in line) || line.mode != "rail" ||
        !("doubleTrack" in line) || line.doubleTrack != 1) {
      OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_REPAIR", "line=" + lineId + " status=stale");
      return false;
    }
    local a = OpexC41BuildPbsAtApproach(("platformA" in line) ? line.platformA : null);
    local b = OpexC41BuildPbsAtApproach(("platformB" in line) ? line.platformB : null);
    local a2 = OpexC41BuildPbsAtApproach(("platformA2" in line) ? line.platformA2 : null,
                                         ("stationA2" in line) ? line.stationA2 : null);
    local b2 = OpexC41BuildPbsAtApproach(("platformB2" in line) ? line.platformB2 : null,
                                         ("stationB2" in line) ? line.stationB2 : null);
    OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_REPAIR", "line=" + lineId + " a=" + a + " b=" + b
                               + " a2=" + a2 + " b2=" + b2);
    if (this._c41RailSignalLines.len() > 0) task.dueCycle = this._taskCycle + 1;
    else task.enabled = false;
    return a == 1 || b == 1 || a2 == 1 || b2 == 1;
  }
  if (task.name == "c41_rail_junction") {
    task.dueCycle = 2147483647;
    if (!C41_RAIL_LOST_JUNCTION_REPAIR || this._c41RailJunctionLines == null) return false;
    local lineId = -1;
    foreach (pendingLine, ignored in this._c41RailJunctionLines) { lineId = pendingLine.tointeger(); break; }
    if (lineId < 0) { task.enabled = false; return false; }
    delete this._c41RailJunctionLines["" + lineId];
    local line = this._findLineById(lineId);
    if (line == null || !("mode" in line) || line.mode != "rail" ||
        !("doubleTrack" in line) || line.doubleTrack != 1) {
      OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_REPAIR", "line=" + lineId + " status=stale");
      return false;
    }
    local exitA = ("platformA" in line && line.platformA != null && ("station_exit" in line.platformA)) ? line.platformA.station_exit : null;
    local exitB = ("platformB" in line && line.platformB != null && ("station_exit" in line.platformB)) ? line.platformB.station_exit : null;
    local leadA = OpexC41RailApproachLead(("platformA" in line) ? line.platformA : null);
    local leadB = OpexC41RailApproachLead(("platformB" in line) ? line.platformB : null);
    local leadA2 = OpexC41RailApproachLead(("platformA2" in line) ? line.platformA2 : null,
                                           ("stationA2" in line) ? line.stationA2 : null);
    local leadB2 = OpexC41RailApproachLead(("platformB2" in line) ? line.platformB2 : null,
                                           ("stationB2" in line) ? line.stationB2 : null);
    local a = OpexC41RepairJunction(leadA, exitA);
    local b = OpexC41RepairJunction(leadB, exitB);
    local a2 = OpexC41RepairJunction(leadA2, ("stationA2" in line) ? line.stationA2 : null);
    local b2 = OpexC41RepairJunction(leadB2, ("stationB2" in line) ? line.stationB2 : null);
    local depot = ("depot" in line) ? line.depot : null;
    local front = (depot != null && AIMap.IsValidTile(depot) && AIRail.IsRailDepotTile(depot))
        ? AIRail.GetRailDepotFrontTile(depot) : null;
    local depotRepair = OpexC41RepairJunction(front, depot);
    local depot2 = ("depot2" in line) && line.depot2 != null ? line.depot2 : -1;
    local front2 = (AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2))
        ? AIRail.GetRailDepotFrontTile(depot2) : null;
    local depot2Repair = OpexC41RepairJunction(front2, depot2);
    OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_REPAIR", "line=" + lineId + " a=" + a + " b=" + b
                                 + " a2=" + a2 + " b2=" + b2 + " depot=" + depotRepair + " depot2=" + depot2Repair);
    if (this._c41RailJunctionLines.len() > 0) task.dueCycle = this._taskCycle + 1;
    else task.enabled = false;
    return a == 1 || b == 1 || a2 == 1 || b2 == 1 || depotRepair == 1 || depot2Repair == 1;
  }
  if (task.name == "report") {
    if (this._lastReportYear == year) return false;
    this._lastReportYear = year;
    if (DECISION_LOG) {
      local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local loan = AICompany.GetLoanAmount();
      OpexDecide("REPORT", "year=" + year + " lines=" + this._lines.len() + " bank=" + bank + " loan=" + loan);
    }
    OpexSign(AIMap.GetTileIndex(1, 1), "LB|" + (year % 100) + "|"
             + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
    if (CASH_RESERVE_PROBE) {
      local calls = CASH_RESERVE_PROBE_CALLS - this._cashReserveProbeLastCalls;
      local minBinds = CASH_RESERVE_PROBE_MIN_BINDS - this._cashReserveProbeLastMinBinds;
      local maxBinds = CASH_RESERVE_PROBE_MAX_BINDS - this._cashReserveProbeLastMaxBinds;
      this._cashReserveProbeLastCalls = CASH_RESERVE_PROBE_CALLS;
      this._cashReserveProbeLastMinBinds = CASH_RESERVE_PROBE_MIN_BINDS;
      this._cashReserveProbeLastMaxBinds = CASH_RESERVE_PROBE_MAX_BINDS;
      OpexCashReserveProbeLog("year=" + year + " calls=" + calls + " min_binds=" + minBinds
                              + " max_binds=" + maxBinds);
    }
    if (PORTFOLIO_REFRESH_PROBE) {
      local checks = PORTFOLIO_REFRESH_PROBE_CHECKS - this._portfolioRefreshProbeLastChecks;
      local gainOk = PORTFOLIO_REFRESH_PROBE_GAIN_OK - this._portfolioRefreshProbeLastGainOk;
      local doubleOk = PORTFOLIO_REFRESH_PROBE_DOUBLE_OK - this._portfolioRefreshProbeLastDoubleOk;
      local doubleOnly = PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY - this._portfolioRefreshProbeLastDoubleOnly;
      this._portfolioRefreshProbeLastChecks = PORTFOLIO_REFRESH_PROBE_CHECKS;
      this._portfolioRefreshProbeLastGainOk = PORTFOLIO_REFRESH_PROBE_GAIN_OK;
      this._portfolioRefreshProbeLastDoubleOk = PORTFOLIO_REFRESH_PROBE_DOUBLE_OK;
      this._portfolioRefreshProbeLastDoubleOnly = PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY;
      local refreshOps = PORTFOLIO_REFRESH_PROBE_REFRESH_OPS - this._portfolioRefreshProbeLastRefreshOps;
      local refreshCount = PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT - this._portfolioRefreshProbeLastRefreshCount;
      this._portfolioRefreshProbeLastRefreshOps = PORTFOLIO_REFRESH_PROBE_REFRESH_OPS;
      this._portfolioRefreshProbeLastRefreshCount = PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT;
      OpexPortfolioRefreshProbeLog("year=" + year + " checks=" + checks + " gain_ok=" + gainOk
                                   + " double_ok=" + doubleOk + " double_only=" + doubleOnly
                                   + " refresh_ops=" + refreshOps + " refresh_count=" + refreshCount);
    }
    /* C41.11 : le rapport exclut son propre cout, publie au plus une fois par an. */
    this._logC41SlackLedger(year);
    this._logC41OpportunityLedger(year);
    this._logC41AdmissionLedger(year);
    this._logC41RailSliceLedger(year);
    this._logC39PassClockLedger(year);
    if (C48_PROJECT_ATTEMPT_LEDGER) this._logC48ProjectAttemptLedger(year);
    if (C49_SCARCITY_LEDGER) this._logC49ScarcityLedger(year);
    if (C55_ORIGIN_RELAX_PROBE) this._logC55OriginRelaxLedger(year);
    if (C54_VEHICLE_ORDERS_PROBE) this._logC54VehicleOrders(year);
    if (C48_INCREMENTAL_PROFILE) this._logC48IncrementalLedger(year);
    this._reportYear(year, this._ranked);
    this._reportLines(year);
    return true;
  }
  if (task.name == "scrap") { this._scrapDeadLines(year); return true; }
  if (task.name == "air") {
    /* C34.1 : sous air_portfolio, la construction aerienne passe EXCLUSIVEMENT par le portefeuille.
     * Motif mesure (docs/taches.md 0 novemquinquagesies) : OpexAirPlans est appele DEUX fois par
     * cycle -- une fois ici (main.nut:971) et une fois dans OpexBuildProjects (projects.nut:693) --
     * et chaque passage coute ~21 jours de temps de jeu. Sur la graine 1, 11 passages ont mange
     * 63 % de l'annee 1. Eteindre cette tache supprime la moitie du goulot, et l'executeur du
     * portefeuille sait deja batir mode == "air" (main.nut:1839). */
    if (AIR_PORTFOLIO) { task.enabled = false; return false; }
    this._tryBuildAir(year); return true;
  }
  if (task.name == "air_fleet") {
    /* C34.2 / C36.2 : sous fleet_portfolio, la croissance de flotte est arbitree par le portefeuille.
     * La tache dediee ne depense plus a l'aveugle, mais inspecte la flotte et injecte
     * les opportunites mures dans le vivier incremental du portefeuille sans attendre un an. */
    task.dueCycle = this._taskCycle + 1;
    if (FLEET_PORTFOLIO) {
      if (PORTFOLIO_CACHE && this._projects != null) {
        local fleetPlan = [];
        this._resizeAirFleets(year, fleetPlan);
        if (fleetPlan.len() > 0) {
          local budgetNow = OpexAvailableCapital();
          this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs);
          this._ranked = this._projects.rail;
        }
      }
      return false;
    }
    return this._resizeAirFleets(year);
  }
  if (task.name == "feeders") {
    if (!FEEDER_ENABLED) { task.enabled = false; return false; }
    /* C32 : sous feeder_portfolio, le rabattement est arbitre par le portefeuille. Laisser AUSSI
     * la tache dediee active batirait la meme ligne deux fois et rendrait l'arbitrage sans objet. */
    if (FEEDER_PORTFOLIO) { task.enabled = false; return false; }
    task.dueCycle = this._taskCycle + 1;
    return this._tryBuildFeeders(year);
  }
  if (task.name == "projects") {
    /* Si l'evenement est arrive apres le passage catalog dans le cycle courant, attendre
     * sa reconstruction plutot que de choisir une ligne dans le vivier devenu obsolete. */
    if (C39_PROJECTS_CADENCE_PROBE) {
      local date = AIDate.GetCurrentDate();
      local tick = AIController.GetTick();
      /* C39.5b : un seul OpexAvailableCapital() par dispatch -- reutilise pour le comptage
       * finançable ET pour le champ capital= ci-dessous, au lieu de l'appeler deux fois pour la
       * meme valeur. isProjectsTurn=true : c'est le seul site qui doit avancer turns/topTurns. */
      local capitalNow = OpexAvailableCapital();
      local financeable = this._c39StampFinanceable(capitalNow, true);
      OpexC39ProjectsCadenceLog("phase=dispatch days_since_last="
          + (this._c39CadenceLastDate >= 0 ? date - this._c39CadenceLastDate : -1)
          + " ticks_since_last="
          + (this._c39CadenceLastTick >= 0 ? tick - this._c39CadenceLastTick : -1)
          + " cycles_since_last="
          + (this._c39CadenceLastCycle >= 0 ? this._taskCycle - this._c39CadenceLastCycle : -1)
          + " rail_search=" + (this._railSearch != null ? 1 : 0)
          + " rail_phase=" + (this._railSearch != null ? this._railSearch.phase : "-")
          + " rail_kind=" + (this._railSearch != null ? this._railSearch.kind : "-")
          + " invalidated=" + (this._portfolioInvalidated ? 1 : 0)
          + " best_len=" + (this._projects != null ? this._projects.best.len() : -1)
          + " capital=" + capitalNow + " financeable=" + financeable);
      this._c39CadenceLastDate = date;
      this._c39CadenceLastTick = tick;
      this._c39CadenceLastCycle = this._taskCycle;
    }
    if (this._portfolioInvalidated) return false;
    return this._tryBuildProjects(year);
  }
  if (task.name == "expand") {
    /* G6§1 : la tache portait UNIQUEMENT sur RAIL_EXPAND, alors que le bloc RAIL_REFLEET
     * (second train, passage en double voie) vit a l'interieur de _expandRailLines. La desactiver
     * sur !RAIL_EXPAND rendait donc rail_refleet injoignable malgre son defaut a 1.
     * Desormais inconditionnel : on ne desactive que si les DEUX sont eteints. */
    if (!RAIL_EXPAND && !RAIL_REFLEET) { task.enabled = false; return false; }
    this._expandRailLines(year);
    return true;
  }
  if (task.name == "refleet") { this._refleetRoadLines(year); return true; }
  if (task.name == "town_growth") {
    if (!TOWN_GROWTH_ENABLED) { task.enabled = false; return false; }
    if (TOWN_GROWTH_SKIP_NOOP && !this._tryTownGrowth(year)) return this._runNextTask();
    else this._tryTownGrowth(year);
    return true;
  }
  if (task.name == "repay") {
    local date = AIDate.GetCurrentDate();
    local ym = year * 12 + AIDate.GetMonth(date);
    if (this._lastRepayMonth == ym) return false;
    this._lastRepayMonth = ym;
    this._tryRepayLoan(year);
    return true;
  }
  task.enabled = false;
  return false;
}

function OpexAI::_rebuildProjects(fleetPlan)
{
  local priorPeak = (this._projects != null && ("capitalBudgetPeak" in this._projects))
      ? this._projects.capitalBudgetPeak : 0;
  local priorHistory = (this._projects != null && ("capitalBudgetHistory" in this._projects))
      ? this._projects.capitalBudgetHistory : null;
  local stage = OPEX_STAGE_COMPLETE;
  local prior = null;
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
    stage = this._generationStage;
    prior = this._projects;
    if (this._generationStageMonth < 0) {
      local date = AIDate.GetCurrentDate();
      this._generationStageMonth = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
    }
  }
  local freightCargo = null;
  local freightCargos = OpexFreightCargoOrder(this._catalog);
  if (freightCargos.len() > 0) {
    if (stage > OPEX_STAGE_AIR_ONLY && stage <= OPEX_STAGE_ROUTE_ONLY
        && this._bootstrapFreightCargo >= 0) {
      freightCargo = this._bootstrapFreightCargo;
    } else {
      local nextCargo = 0;
      if (this._lastFreightCargo >= 0) {
        for (local i = 0; i < freightCargos.len(); i++) {
          if (freightCargos[i] == this._lastFreightCargo) {
            nextCargo = (i + 1) % freightCargos.len();
            break;
          }
        }
      }
      freightCargo = freightCargos[nextCargo];
    }
  }
  this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
      priorPeak, priorHistory, fleetPlan, this._abandonedPairs, stage, prior,
      freightCargo, freightCargos, this._waterSiteCatalog);
  local actualFreightCargo = (this._projects != null && ("freightCargo" in this._projects))
      ? this._projects.freightCargo : freightCargo;
  if (stage == OPEX_STAGE_AIR_ONLY && actualFreightCargo != null) {
    this._bootstrapFreightCargo = actualFreightCargo;
  }
  /* Le bootstrap utilise le meme premier cargo pour son rail (etape 0) puis
   * sa route (etape 3). Ensuite chaque passe complete ne porte que sur le
   * cargo suivant : prior reste null en regime complet, donc le portefeuille
   * ne regrossit jamais par accumulation des anciens lots fret. */
  if (freightCargos.len() > 0
      && (stage == OPEX_STAGE_ROUTE_ONLY || stage == OPEX_STAGE_COMPLETE)) {
    if (actualFreightCargo != null) this._lastFreightCargo = actualFreightCargo;
    if (stage == OPEX_STAGE_ROUTE_ONLY) this._bootstrapFreightCargo = -1;
  }
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
    this._generationStage++;
    if (DECISION_LOG) {
      OpexDecide("BOOTSTRAP_ADVANCE", "next=" + this._generationStage
                 + " funded=" + this._projects.best.len());
    }
    local b = (this._catalog != null && this._catalog.bounds != null)
        ? this._catalog.bounds : null;
    if (b != null) {
      OpexSign(AIMap.GetTileIndex(1, 2), "BS|" + (this._generationStage - 1)
               + "|" + b.railMin + "|" + b.railMax + "|" + b.airMin);
    }
  }
}

function OpexAI::Save()
{
  local abandoned = {};
  if (this._abandonedPairs != null) {
    foreach (key, val in this._abandonedPairs) abandoned[key] <- val;
  }
  /* A 0, conserver exactement le format historique : la charge complete est experimentale et
   * le serialiseur execute Save() sous budget d'opcodes. */
  if (!SAVE_FULL_STATE) return {
    version = 1,
    generationStage = this._generationStage,
    generationStageMonth = this._generationStageMonth,
    lastFreightCargo = this._lastFreightCargo,
    bootstrapFreightCargo = this._bootstrapFreightCargo,
    nextLineId = this._nextLineId,
    lastCatalogMonth = this._lastCatalogMonth,
    lastReportYear = this._lastReportYear,
    startYear = this._startYear,
    abandonedPairs = abandoned,
    airBuilt = this._airBuilt,
    waterBuilt = this._waterBuilt,
    waterSiteCatalog = this._waterSiteCatalog,
  };

  local taskDue = {};
  if (this._taskQueue != null) {
    foreach (task in this._taskQueue) taskDue[task.name] <- task.dueCycle;
  }
  /* Les lignes sont normalement donnees telles quelles au serialiseur. Certains modeles
   * economiques (surtout air) laissent toutefois des flottants dans des metriques predites,
   * type que le format de sauvegarde OpenTTD refuse. Une projection superficielle n'est faite
   * que dans ce cas : les champs scalarises restants sont tous serialisables; les tableaux
   * (VehicleID) et tables des lignes actuelles ne contiennent que des entiers/booleens/null. */
  local saveLines = this._lines;
  local projectedLines = null;
  if (this._lines != null) {
    for (local i = 0; i < this._lines.len(); i++) {
      local line = this._lines[i];
      local needsProjection = line != null && typeof line == "table";
      if (needsProjection) {
        needsProjection = false;
        foreach (key, val in line) {
          local valType = typeof val;
          if (valType != "integer" && valType != "string" && valType != "bool" &&
              valType != "null" && valType != "array" && valType != "table") {
            needsProjection = true;
            break;
          }
        }
      }
      if (needsProjection) {
        if (projectedLines == null) {
          projectedLines = [];
          for (local prior = 0; prior < i; prior++) projectedLines.append(this._lines[prior]);
        }
        local serializableLine = {};
        foreach (key, val in line) {
          local valType = typeof val;
          if (valType == "integer" || valType == "string" || valType == "bool" ||
              valType == "null" || valType == "array" || valType == "table") {
            serializableLine[key] <- val;
          } else if (valType == "float") {
            /* Le format de sauvegarde n'admet pas le flottant : arrondir CONSERVE le champ (une
             * metrique predite), alors que le jeter le perdrait en silence au rechargement. */
            serializableLine[key] <- val.tointeger();
          }
        }
        projectedLines.append(serializableLine);
      } else if (projectedLines != null) {
        projectedLines.append(line);
      }
    }
  }
  if (projectedLines != null) saveLines = projectedLines;
  return {
    version = 1,
    generationStage = this._generationStage,
    generationStageMonth = this._generationStageMonth,
    lastFreightCargo = this._lastFreightCargo,
    bootstrapFreightCargo = this._bootstrapFreightCargo,
    nextLineId = this._nextLineId,
    lastCatalogMonth = this._lastCatalogMonth,
    lastReportYear = this._lastReportYear,
    startYear = this._startYear,
    abandonedPairs = abandoned,
    airBuilt = this._airBuilt,
    waterBuilt = this._waterBuilt,
    waterSiteCatalog = this._waterSiteCatalog,
    lines = saveLines,
    abandonCounts = this._abandonCounts,
    lastRepayMonth = this._lastRepayMonth,
    taskCycle = this._taskCycle,
    taskCursor = this._taskCursor,
    vehiclesToScrap = this._vehiclesToScrap,
    taskDue = taskDue,
    stateVersion = 1,
  };
}

function OpexAI::Load(version, data)
{
  this._loadedFromSave = true;
  if (data == null) return;
  if ("generationStage" in data) this._generationStage = data.generationStage;
  if ("generationStageMonth" in data) this._generationStageMonth = data.generationStageMonth;
  if ("lastFreightCargo" in data) this._lastFreightCargo = data.lastFreightCargo;
  if ("bootstrapFreightCargo" in data) this._bootstrapFreightCargo = data.bootstrapFreightCargo;
  if ("nextLineId" in data) this._nextLineId = data.nextLineId;
  if ("lastCatalogMonth" in data) this._lastCatalogMonth = data.lastCatalogMonth;
  if ("lastReportYear" in data) this._lastReportYear = data.lastReportYear;
  if ("startYear" in data) this._startYear = data.startYear;
  if ("airBuilt" in data) this._airBuilt = data.airBuilt;
  if ("waterBuilt" in data) this._waterBuilt = data.waterBuilt;
  if ("waterSiteCatalog" in data && data.waterSiteCatalog != null &&
      ("towns" in data.waterSiteCatalog)) {
    this._waterSiteCatalog = data.waterSiteCatalog;
  }
  if ("abandonedPairs" in data && data.abandonedPairs != null) {
    this._abandonedPairs = {};
    foreach (key, val in data.abandonedPairs) this._abandonedPairs[key] <- val;
  }
  if ("lines" in data) this._pendingLines = data.lines;
  if ("abandonCounts" in data && data.abandonCounts != null) this._abandonCounts = data.abandonCounts;
  if ("lastRepayMonth" in data) this._lastRepayMonth = data.lastRepayMonth;
  if ("taskCycle" in data) this._taskCycle = data.taskCycle;
  if ("taskCursor" in data) this._taskCursor = data.taskCursor;
  if ("vehiclesToScrap" in data && data.vehiclesToScrap != null) this._vehiclesToScrap = data.vehiclesToScrap;
  /* Cle par nom : l'ordre de la file peut evoluer entre deux versions de l'IA. */
  if ("taskDue" in data && data.taskDue != null && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name in data.taskDue) task.dueCycle = data.taskDue[task.name];
    }
  }
}

/* Load tourne trop tot et sous DisableDoCommandScope : la verification du monde est donc faite
 * ici, apres les reglages. Les stationA/stationB sont des TUILES, jamais des StationID. */
function OpexAI::_reconcileAfterLoad()
{
  local saved = 0;
  local kept = 0;
  local dropped = 0;
  local purgedVehicles = 0;
  local liveLines = [];
  if (this._pendingLines != null) {
    foreach (line in this._pendingLines) {
      saved++;
      if (line == null || !("stationA" in line) || !("stationB" in line) ||
          !AIMap.IsValidTile(line.stationA) || !AIMap.IsValidTile(line.stationB)) {
        dropped++;
        continue;
      }
      local stationA = AIStation.GetStationID(line.stationA);
      local stationB = AIStation.GetStationID(line.stationB);
      if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) ||
          !AICompany.IsMine(AITile.GetOwner(line.stationA)) ||
          !AICompany.IsMine(AITile.GetOwner(line.stationB))) {
        dropped++;
        continue;
      }
      /* Les camions sont identifies par leurs ordres : ne pas reecrire le champ vehicles d'une
       * ligne route, meme si une ancienne version l'a laisse dans la table. */
      if ((!("mode" in line) || line.mode != "road") && ("vehicles" in line) && line.vehicles != null) {
        local liveVehicles = [];
        foreach (vehicle in line.vehicles) {
          if (AIVehicle.IsValidVehicle(vehicle)) liveVehicles.append(vehicle);
          else purgedVehicles++;
        }
        line.vehicles = liveVehicles;
      }
      liveLines.append(line);
      kept++;
    }
  }
  this._lines = liveLines;
  this._pendingLines = null;
  /* Sans sonde : cette unique preuve doit toujours accompagner un rechargement, jamais une partie neuve. */
  OpexDecide("LOAD_RECONCILE", "saved=" + saved + " kept=" + kept + " dropped=" + dropped + " vehicles_purged=" + purgedVehicles);
}

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  /* Lu une seule fois : le reglage ne change pas en cours de partie, et OpexSign est appele des
   * dizaines de fois par an. Un GetSetting par appel serait du gaspillage pur. */
  DEBUG_SIGNS = AIController.GetSetting("debug_signs") != 0;
  SAVE_FULL_STATE = AIController.GetSetting("save_full_state") != 0;
  /* Exprime en milliers dans le reglage : AddSetting ne porte que des entiers, et un pas de
   * 50 000 sur une plage de 0 a 2 000 000 serait illisible en unites brutes. */
  LOAN_REPAY_FLOOR = AIController.GetSetting("loan_repay_floor_k") * 1000;
  /* Memes reglages lus UNE fois : OpexIterationBudget et _tryBuild tournent pour chaque candidat,
   * donc les GetSetting dans ces boucles seraient du debit d'opcodes perdu. */
  HARD_ITERATION_CAP = AIController.GetSetting("pathfinder_hard_cap_k") * 1000;
  RAIL_SEARCH_RESUMABLE = AIController.GetSetting("rail_search_resumable") != 0;
  RAIL_MICRO_DEADLINE = AIController.GetSetting("rail_micro_deadline") != 0;
  RAIL_SEGMENTED_SEARCH = AIController.GetSetting("rail_segmented_search") != 0;
  DECISION_LOG = AIController.GetSetting("decision_log") != 0;
  PORTFOLIO_LOG = DECISION_LOG;
  ABANDON_MEMORY = AIController.GetSetting("abandon_memory") != 0;
  local acd = AIController.GetSetting("abandon_cooldown_days");
  if (acd >= 0) ABANDON_COOLDOWN_DAYS = acd;
  ABANDON_GEN_FILTER = AIController.GetSetting("abandon_gen_filter") != 0;
  STATION_JOIN = AIController.GetSetting("station_join") != 0;
  JOIN_MAX_DISTANCE = AIController.GetSetting("join_max_distance");
  JOIN_PLACE = AIController.GetSetting("join_place") != 0;
  ORIGIN_SITABLE = AIController.GetSetting("origin_sitable") != 0;
  BASIN_SHARE = AIController.GetSetting("basin_share") != 0;
  REBORROW = AIController.GetSetting("reborrow") != 0;
  /* Lu ici comme les autres reglages de decision : catalog.refresh le consulte des le premier
   * cycle annuel, qui a lieu apres Start(). */
  ROAD_BUILD_ENABLED = AIController.GetSetting("road_mode") != 0;
  ROAD_PAX_BUILD_ENABLED = AIController.GetSetting("road_pax_build") != 0;
  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  TOWN_GROWTH_SKIP_NOOP = AIController.GetSetting("town_growth_skip_noop") != 0;
  local roadPaxCatchment = AIController.GetSetting("road_pax_catchment_pct");
  if (roadPaxCatchment > 0) ROAD_PAX_CATCHMENT_SHARE_PCT = roadPaxCatchment;
  local roadStopHouses = AIController.GetSetting("road_stop_catchment_houses");
  if (roadStopHouses > 0) ROAD_STOP_CATCHMENT_HOUSES = roadStopHouses;
  local roadPaxDwell = AIController.GetSetting("road_pax_dwell_days");
  if (roadPaxDwell >= 0) ROAD_PAX_STOP_DWELL_DAYS = roadPaxDwell;
  local airPaxCalibration = AIController.GetSetting("air_pax_revenue_calibration_pct");
  if (airPaxCalibration > 0) AIR_PAX_REVENUE_CALIBRATION_PCT = airPaxCalibration;
  ROAD_REFLEET = AIController.GetSetting("road_refleet") != 0;
  ROAD_MULTISTOP = AIController.GetSetting("road_multistop") != 0;
  MARGINAL_FLEET = AIController.GetSetting("marginal_fleet") != 0;
  FEEDER_PORTFOLIO = AIController.GetSetting("feeder_portfolio") != 0;
  AIR_PORTFOLIO = AIController.GetSetting("air_portfolio") != 0;
  FLEET_PORTFOLIO = AIController.GetSetting("fleet_portfolio") != 0;
  TENSION_SCORING = AIController.GetSetting("tension_scoring") != 0;
  local dfp = AIController.GetSetting("decision_friction_permille");
  if (dfp >= 0) TENSION_DECISION_FRICTION = dfp.tofloat() / 1000.0;
  SHADOW_PRICING = AIController.GetSetting("shadow_pricing") != 0;
  FLAT_BONUS = AIController.GetSetting("flat_bonus") != 0;
  AIR_ROI_ORDER = AIController.GetSetting("air_roi_order") != 0;
  LOOP_BUDGET = AIController.GetSetting("loop_budget") != 0;
  PORTFOLIO_V2 = AIController.GetSetting("portfolio_v2") != 0;
  PORTFOLIO_MAX_BATCH = AIController.GetSetting("portfolio_max_batch");
  PORTFOLIO_DYNAMIC_BATCH = AIController.GetSetting("portfolio_dynamic_batch") != 0;
  local dynamicRejectLimit = AIController.GetSetting("dynamic_batch_reject_limit");
  if (dynamicRejectLimit >= 0) DYNAMIC_BATCH_REJECT_LIMIT = dynamicRejectLimit;
  local dynamicOpsBudget = AIController.GetSetting("dynamic_batch_ops_budget_pct");
  if (dynamicOpsBudget >= 0) DYNAMIC_BATCH_OPS_BUDGET_PCT = dynamicOpsBudget;
  PORTFOLIO_FLOOR_PCT = AIController.GetSetting("portfolio_floor_pct");
  FLEET_FIX = AIController.GetSetting("fleet_fix") != 0;
  ECONOMY_FIX = AIController.GetSetting("economy_fix") != 0;
  GROWTH_YIELDS = AIController.GetSetting("growth_yields") != 0;
  AIR_MARGIN = AIController.GetSetting("air_margin") != 0;
  AIR_ABANDON = AIController.GetSetting("air_abandon") != 0;
  STAGED_BOOTSTRAP = AIController.GetSetting("staged_bootstrap") != 0;
  if (!STAGED_BOOTSTRAP) this._generationStage = OPEX_STAGE_COMPLETE;
  PRICING_ROAD_RATING = AIController.GetSetting("pricing_road_rating") != 0;
  PRICING_RAIL_DEPOT = AIController.GetSetting("pricing_rail_depot") != 0;
  PRICING_ROAD_OPS = AIController.GetSetting("pricing_road_ops") != 0;
  RAIL_COST_PROBE = AIController.GetSetting("rail_cost_probe") != 0;
  AIR_COST_PROBE = AIController.GetSetting("air_cost_probe") != 0;
  ROAD_COST_PROBE = AIController.GetSetting("road_cost_probe") != 0;
  AIR_PRESITE = AIController.GetSetting("air_presite") != 0;
  PORTFOLIO_FRESH_BUDGET = AIController.GetSetting("portfolio_fresh_budget") != 0;
  PORTFOLIO_CACHE = AIController.GetSetting("portfolio_cache") != 0;
  AIR_FLEET_PROBE = AIController.GetSetting("air_fleet_probe") != 0;
  FLEET_BEFORE_NEW = AIController.GetSetting("fleet_before_new") != 0;
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
  local tc = AIController.GetSetting("transit_cost");
  if (tc >= 0) TRANSIT_COST_PERMILLE = tc;
  RAIL_DEVIS = AIController.GetSetting("rail_devis") != 0;
  RAIL_EXPAND = AIController.GetSetting("rail_expand") != 0;
  ASTAR_COST_V2 = AIController.GetSetting("astar_cost") != 0;
  PROBE_NEGATIVE = AIController.GetSetting("probe_negative") != 0;
  PAX_NEAR = AIController.GetSetting("pax_near") != 0;
  DYNAMIC_CASH_RESERVE = AIController.GetSetting("dynamic_cash_reserve") != 0;
  RESERVE_MAINT_CAP = AIController.GetSetting("reserve_maint_cap") != 0;
  AIR_MARGIN_V2 = AIController.GetSetting("air_margin_v2") != 0;
  KNAPSACK_ROI = AIController.GetSetting("knapsack_roi") != 0;
  POOL_FINANCEABLE = AIController.GetSetting("pool_financeable") != 0;
  CAPITAL_CALIBRATION = AIController.GetSetting("capital_calibration") != 0;
  RAIL_PREQUOTE = AIController.GetSetting("rail_prequote") != 0;
  RAIL_PREQUOTE_KEEP_PLAN = AIController.GetSetting("rail_prequote_keep_plan") != 0;
  RAIL_TERRAIN_PROBE = AIController.GetSetting("rail_terrain_probe") != 0;
  ABANDON_MEMORY_TRANSIENT_GUARD = AIController.GetSetting("abandon_memory_transient_guard") != 0;
  AIR_HUB_FIX = AIController.GetSetting("air_hub_fix") != 0;
  TENSION_PROBE = AIController.GetSetting("tension_probe") != 0;
  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
    OpexTensionEnable(this._budget);
  }
  AIR_DEMAND_CAP = AIController.GetSetting("air_demand_cap") != 0;
  AIR_DEMAND_PLAN = AIController.GetSetting("air_demand_plan") != 0;
  DYNAMIC_PATHFINDER_CAP = AIController.GetSetting("dynamic_pathfinder_cap") != 0;
  PAX_FULL_LOAD = AIController.GetSetting("pax_full_load") != 0;
  AIR_FULL_LOAD = AIController.GetSetting("air_full_load") != 0;
  COMPLEX_CARGO = AIController.GetSetting("complex_cargo") != 0;
  AIR_HUB = AIController.GetSetting("air_hub") != 0;
  local airMaxDist = AIController.GetSetting("air_max_distance");
  if (airMaxDist >= 0) AIR_MAX_DISTANCE = airMaxDist;
  local afcd = AIController.GetSetting("air_fleet_cadence_days");
  if (afcd >= 0) AIR_FLEET_CADENCE_DAYS = afcd;
  local afb = AIController.GetSetting("air_fleet_buffer");
  if (afb >= -1) AIR_FLEET_BUFFER = afb;
  local rtf = AIController.GetSetting("rail_terrain_factor");
  if (rtf > 0) RAIL_TERRAIN_FACTOR = rtf;
  local ptk = AIController.GetSetting("project_top_k");
  if (ptk > 0) PROJECT_TOP_K = ptk;
  PROJECT_TOP_K_DYNAMIC = AIController.GetSetting("project_top_k_dynamic") != 0;
  RAIL_REFLEET = AIController.GetSetting("rail_refleet") != 0;
  FEEDER_ENABLED = AIController.GetSetting("feeder_enabled") != 0;
  FEEDER_CANDIDATES_ENABLED = AIController.GetSetting("feeder_candidates") != 0;
  EVENT_DEPOT_SELL = AIController.GetSetting("event_depot_sell") != 0;
  EVENT_INDUSTRY_CLOSE = AIController.GetSetting("event_industry_close") != 0;
  EVENT_SUBSIDY_PROBE = AIController.GetSetting("event_subsidy_probe") != 0;
  EVENT_VEHICLE_LOST = AIController.GetSetting("event_vehicle_lost") != 0;
  EVENT_CATALOG_INVALIDATE = AIController.GetSetting("event_catalog_invalidate") != 0;
  C39_INVALIDATION_PROBE = AIController.GetSetting("c39_invalidation_probe") != 0;
  C39_DECISION_DELTA_PROBE = AIController.GetSetting("c39_decision_delta_probe") != 0;
  C39_AIR_REASON_PROBE = AIController.GetSetting("c39_air_reason_probe") != 0;
  C39_ENGINE_REFRESH = AIController.GetSetting("c39_engine_refresh") != 0;
  C41_REVISION_PROBE = AIController.GetSetting("c41_revision_probe") != 0;
  C41_WATER_REFRESH = AIController.GetSetting("c41_water_refresh") != 0;
  C41_WATER_PRECHECK = AIController.GetSetting("c41_water_precheck") != 0;
  C41_WATER_CANDIDATE_PROBE = AIController.GetSetting("c41_water_candidate_probe") != 0
      && C41_WATER_PRECHECK;
  C41_WATER_PLANS_PROFILE = AIController.GetSetting("c41_water_plans_profile") != 0
      && C41_WATER_CANDIDATE_PROBE;
  C41_WATER_SITE_PROFILE = AIController.GetSetting("c41_water_site_profile") != 0
      && C41_WATER_PLANS_PROFILE;
  WATER_LAKES_CONNECTIVITY = AIController.GetSetting("water_lakes_connectivity") != 0;
  WATER_SITE_CATALOG = AIController.GetSetting("water_site_catalog") != 0;
  WATER_DISCOVERY_REAL_FRONTS = AIController.GetSetting("water_discovery_real_fronts") != 0;
  C41_SLACK_LEDGER = AIController.GetSetting("c41_slack_ledger") != 0;
  C41_MONTHLY_BUSY_LEDGER = AIController.GetSetting("c41_monthly_busy_ledger") != 0;
  C41_STALENESS_LEDGER = AIController.GetSetting("c41_staleness_ledger") != 0;
  C41_OPPORTUNITY_LEDGER = AIController.GetSetting("c41_opportunity_ledger") != 0;
  C41_ADMISSION_LEDGER = AIController.GetSetting("c41_admission_ledger") != 0;
  C41_ROAD_REFRESH = AIController.GetSetting("c41_road_refresh") != 0;
  C41_ROAD_CANDIDATE_PROFILE = AIController.GetSetting("c41_road_candidate_profile") != 0;
  C41_ROAD_FREIGHT_PROFILE = AIController.GetSetting("c41_road_freight_profile") != 0;
  C41_ROAD_FREIGHT_SERVED_INDEX = AIController.GetSetting("c41_road_freight_served_index") != 0;
  C41_ROAD_FREIGHT_TOWN_PROFILE = AIController.GetSetting("c41_road_freight_town_profile") != 0;
  C41_ROAD_FREIGHT_ACCEPTANCE_INDEX = AIController.GetSetting("c41_road_freight_acceptance_index") != 0;
  C41_ROAD_FEEDER_PROFILE = AIController.GetSetting("c41_road_feeder_profile") != 0;
  C41_RAIL_PORTFOLIO_PROFILE = AIController.GetSetting("c41_rail_portfolio_profile") != 0;
  C41_RAIL_CANDIDATE_PROFILE = AIController.GetSetting("c41_rail_candidate_profile") != 0;
  C41_RAIL_PAX_PROFILE = AIController.GetSetting("c41_rail_pax_profile") != 0;
  C41_RAIL_PAX_CANDIDATE_PROFILE = AIController.GetSetting("c41_rail_pax_candidate_profile") != 0;
  C41_RAIL_PAX_ECONOMICS_PROFILE = AIController.GetSetting("c41_rail_pax_economics_profile") != 0;
  C41_RAIL_PAX_SPEED_PROFILE = AIController.GetSetting("c41_rail_pax_speed_profile") != 0;
  C41_RAIL_PAX_SPEED_DETAIL_PROFILE = AIController.GetSetting("c41_rail_pax_speed_detail_profile") != 0;
  C41_RAIL_PAX_CRUISE_PROFILE = AIController.GetSetting("c41_rail_pax_cruise_profile") != 0;
  C41_RAIL_PAX_CRUISE_CACHE = AIController.GetSetting("c41_rail_pax_cruise_cache") != 0;
  C41_RAIL_FREIGHT_PROFILE = AIController.GetSetting("c41_rail_freight_profile") != 0;
  C41_RAIL_FREIGHT_CANDIDATE_PROFILE = AIController.GetSetting("c41_rail_freight_candidate_profile") != 0;
  C41_RAIL_FREIGHT_ECONOMICS_PROFILE = AIController.GetSetting("c41_rail_freight_economics_profile") != 0;
  C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE = AIController.GetSetting("c41_rail_freight_economics_detail_profile") != 0;
  C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE = AIController.GetSetting("c41_rail_freight_economics_setup_profile") != 0;
  C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE = AIController.GetSetting("c41_rail_freight_economics_consist_profile") != 0;
  C41_RAIL_FREIGHT_CRUISE_PROFILE = AIController.GetSetting("c41_rail_freight_cruise_profile") != 0;
  C41_RAIL_FREIGHT_CRUISE_CACHE = AIController.GetSetting("c41_rail_freight_cruise_cache") != 0;
  C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE = AIController.GetSetting("c41_rail_freight_speed_detail_profile") != 0;
  C41_RAIL_FREIGHT_ACCELERATION_CACHE = AIController.GetSetting("c41_rail_freight_acceleration_cache") != 0;
  C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE = AIController.GetSetting("c41_rail_freight_effective_speed_profile") != 0;
  C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE = AIController.GetSetting("c41_rail_freight_town_guards_profile") != 0;
  C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE = AIController.GetSetting("c41_rail_freight_town_service_cache") != 0;
  C41_RAIL_LOST_PROBE = AIController.GetSetting("c41_rail_lost_probe") != 0;
  C41_RAIL_LOST_TOPOLOGY_PROBE = AIController.GetSetting("c41_rail_lost_topology_probe") != 0;
  C41_RAIL_LOST_PHYSICAL_PROBE = AIController.GetSetting("c41_rail_lost_physical_probe") != 0;
  C41_RAIL_LOST_SIGNAL_REPAIR = AIController.GetSetting("c41_rail_lost_signal_repair") != 0;
  C41_RAIL_LOST_CONNECTIVITY_PROBE = AIController.GetSetting("c41_rail_lost_connectivity_probe") != 0;
  C41_RAIL_LOST_JUNCTION_REPAIR = AIController.GetSetting("c41_rail_lost_junction_repair") != 0;
  C41_RAIL_SLICE_LEDGER = AIController.GetSetting("c41_rail_slice_ledger") != 0;
  C41_RAIL_CASH_RELEASE = AIController.GetSetting("c41_rail_cash_release") != 0;
  C41_RAIL_DOMINATION_PROBE = AIController.GetSetting("c41_rail_domination_probe") != 0;
  C41_PROJECTS_FALLTHROUGH_PROBE = AIController.GetSetting("c41_projects_fallthrough_probe") != 0;
  C39_PROJECTS_CADENCE_PROBE = AIController.GetSetting("c39_projects_cadence_probe") != 0;
  C39_PASS_CLOCK_LEDGER = AIController.GetSetting("c39_pass_clock_ledger") != 0;
  C48_PROJECT_ATTEMPT_LEDGER = AIController.GetSetting("c48_project_attempt_ledger") != 0;
  C49_SCARCITY_LEDGER = AIController.GetSetting("c49_scarcity_ledger") != 0;
  C55_ORIGIN_RELAX_PROBE = AIController.GetSetting("c55_origin_relax_probe") != 0;
  C54_VEHICLE_ORDERS_PROBE = AIController.GetSetting("c54_vehicle_orders_probe") != 0;
  if (C49_SCARCITY_LEDGER) {
    this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
        decision_attempted = 0, decision_unattempted = 0, none = 0 };
    this._c49ScarcityRegime = "cash";
  }
  if (C55_ORIGIN_RELAX_PROBE) {
    C55_ORIGIN_RELAX_LEDGER = {
      candidates_seen = 0, rejected_total = 0, both_served = 0, one_served = 0,
      one_served_pax = 0, one_served_freight = 0, duplicate_exact = 0,
      total_candidates_seen = 0, total_rejected_total = 0, total_both_served = 0,
      total_one_served = 0, total_one_served_pax = 0, total_one_served_freight = 0,
      total_duplicate_exact = 0,
    };
  }
  C48_INCREMENTAL_PROFILE = AIController.GetSetting("c48_incremental_profile") != 0;
  CASH_RESERVE_PROBE = AIController.GetSetting("cash_reserve_probe") != 0;
  PORTFOLIO_REFRESH_PROBE = AIController.GetSetting("portfolio_refresh_probe") != 0;
  if (C41_RAIL_LOST_TOPOLOGY_PROBE) C41_RAIL_LOST_PROBE = true;
  if (C41_RAIL_LOST_PHYSICAL_PROBE) C41_RAIL_LOST_PROBE = true;
  if (C41_RAIL_LOST_SIGNAL_REPAIR) C41_RAIL_LOST_PROBE = true;
  if (C41_RAIL_LOST_CONNECTIVITY_PROBE) C41_RAIL_LOST_PROBE = true;
  if (C41_RAIL_LOST_JUNCTION_REPAIR) C41_RAIL_LOST_PROBE = true;
  C41_VEHICLE_LOST_PROBE = AIController.GetSetting("c41_vehicle_lost_probe") != 0
      || C41_RAIL_LOST_PROBE || C41_RAIL_LOST_TOPOLOGY_PROBE || C41_RAIL_LOST_PHYSICAL_PROBE
      || C41_RAIL_LOST_SIGNAL_REPAIR || C41_RAIL_LOST_CONNECTIVITY_PROBE || C41_RAIL_LOST_JUNCTION_REPAIR;
  if (C41_WATER_REFRESH && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name == "c41_water") { task.enabled = true; break; }
    }
  }
  if (C41_ROAD_REFRESH && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name == "c41_road") { task.enabled = true; break; }
    }
  }
  VIVIER_RATIO_FILTER = AIController.GetSetting("vivier_ratio_filter") != 0;
  ROAD_FLEET_FIX = AIController.GetSetting("road_fleet_fix") != 0;
  AIR_FLEET_LINE_PRICE = AIController.GetSetting("air_fleet_line_price") != 0;
  AIR_CADENCE_CAP = AIController.GetSetting("air_cadence_cap") != 0;
  ROAD_LOADING_FIX = AIController.GetSetting("road_loading_fix") != 0;
  CLEAN_DENSITY_SCORE = AIController.GetSetting("clean_density_score") != 0;
  local ccc = AIController.GetSetting("capital_ceiling_cycles");
  if (ccc >= 0) CAPITAL_CEILING_CYCLES = ccc;
  local iap = AIController.GetSetting("infra_amort_pct");
  if (iap >= 0) INFRA_AMORT_PCT = iap;
  FEEDER_UNLOCK = AIController.GetSetting("feeder_unlock") != 0;
  FEEDER_PRICING = AIController.GetSetting("feeder_pricing") != 0;
  FEEDER_TOWN_COVERAGE = AIController.GetSetting("feeder_town_coverage") != 0;
  FEEDER_MAIL_DUPLICATE = AIController.GetSetting("feeder_mail_duplicate") != 0;
  FEEDER_HUB_CHECK = AIController.GetSetting("feeder_hub_check") != 0;
  local fhwm = AIController.GetSetting("feeder_hub_wait_max");
  if (fhwm >= 0) FEEDER_HUB_WAIT_MAX = fhwm;
  local fhmd = AIController.GetSetting("feeder_hub_min_days");
  if (fhmd >= 0) FEEDER_HUB_MIN_DAYS = fhmd;
  AIR_SITE_CACHE_ENABLED = AIController.GetSetting("air_site_cache") != 0;
  AIR_CHEAP_SITE = AIController.GetSetting("air_cheap_site") != 0;
  AIR_JOINED_STOPS = AIController.GetSetting("air_joined_stops") != 0;
  ROAD_CHEAP_TRACE = AIController.GetSetting("road_cheap_trace") != 0;
  ROAD_PAX_VOIRIE = AIController.GetSetting("road_pax_voirie") != 0;
  ROAD_PAX_OVERLAP = AIController.GetSetting("road_pax_overlap") != 0;
  if (this._loadedFromSave) this._reconcileAfterLoad();
  if (DECISION_LOG) {
    OpexDecide("SETTINGS", "road_cheap_trace=" + ROAD_CHEAP_TRACE
               + " raw=" + AIController.GetSetting("road_cheap_trace")
               + " road_pax_build=" + ROAD_PAX_BUILD_ENABLED
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
  if (!this._loadedFromSave) {
    /* Le reload reprend la dette effectivement choisie : ne pas reemprunter sans decision. */
    AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=initial_borrow amount=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount());
    }
  }

  while (true) {
    this._processEvents();
    if (LOOP_BUDGET) {
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
