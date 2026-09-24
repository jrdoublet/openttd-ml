/* C65 passe 2 : globales du bloc AVANT require(budget/catalog/...). */
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
 * le fret routier et les lignes deja construites restent actifs. Le defaut faux privilegie le
 * profit des aeroports ; le banc peut reconstituer le bras bus avec
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
/* C33.2 : Arrets de rabattement joints dans le chantier aeroport */
AIR_JOINED_STOPS <- false;
/* B9/G4 : sonde passive post-chantier du catchment AIR. Defaut 0 : aucune tuile
 * supplementaire n'est inspectee dans le comportement livre. */
AIR_CATCHMENT_PROBE <- false;
/* M3/G12 : sonde passive du choix de materiel avant ROI. Elle n'est jamais lue par les
 * regles de selection ; elle autorise uniquement les comparatifs et logs de diagnostic. */
EQUIPMENT_ROI_PROBE <- false;
/* C68 : politique causale issue de M3. A sites, aeroport, demande et admission identiques,
 * choisir l'appareil compatible qui maximise le profit predit de CETTE route. Adoptee apres
 * autorite 20x10 C66.4 du 2026-09-17. */
AIR_ROUTE_PLANE_SELECTION <- true;
/* Nombre maximal d'arrets bus annexes partageant directement le StationID de l'aeroport. */
AIR_JOINED_STOP_LIMIT <- 2;
/* Early-slot experimental: prioritise profitable air projects that claim a first
 * airport in large towns before competitors can consume both town slots. */
AIR_EARLY_SLOT <- false;
AIR_EARLY_SLOT_TARGET_TOWNS <- 6;
AIR_EARLY_SLOT_MIN_POP <- 1000;
AIR_EARLY_SLOT_BONUS_PCT <- 50;
/* C83.1 : objectif territorial distinct du bonus early-slot historique.
 * L'ablation du 2026-09-24 a teste 24 villes, mais les 18 villes marginales
 * ajoutaient des courses moins propres et degradaient la valeur au 5x6 ;
 * conserver le coeur des 6 plus grandes villes tant qu'un elargissement n'est
 * pas requalifie. */
AIR_C83_TARGET_TOWNS <- 6;
/* Refaire le sac a dos contre la caisse vivante, sans repayer la generation des candidats. */
/* C36.1 : Caching incremental du vivier post-chantier. */
/* Compatibilite de cadence VM apres suppression des flags economy morts. Constante interne, jamais configurable ni vraie. */
OPEX_ECONOMY_OPCODE_COMPAT_FALSE <- false;
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
/* Compatibilite d'opcodes des anciens flags WATER tous forces false. Ce slot ne pilote
 * aucune fonctionnalite et ne possede aucun reglage utilisateur. */
WATER_OPCODE_COMPAT_FALSE <- false;
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
/* C49 etape 1 : sonde strictement observatoire de la cause prochaine du projet non bati.
 * Le repli 0 ne doit atteindre ni lecture de tresorerie finale, ni plafond de vehicules, ni
 * allocation de ledger. */
C49_SCARCITY_LEDGER <- false;
/* C55 etape 1 : mesure seule du filtre OR route. Le ledger est nul hors sonde. */
C55_ORIGIN_RELAX_PROBE <- false;
C55_ORIGIN_RELAX_LEDGER <- null;
/* C55 etape 2 : relache seulement le verrou d'origine du fret route. */
C55_FREIGHT_ORIGIN_RELAX <- false;
/* C55 : sonde de tracabilite des revalidations PAX routieres bloquees par une origine deja servie. */
C55_PAX_TRACE_PROBE <- false;
C55_PAX_TRACE_LEDGER <- null;
/* C60 : Sonde d'exposition aux notes municipales. */
C60_TOWN_RATING_PROBE <- false;
C60_TOWN_RATING_LEDGER <- null;
/* C56 : trace immediate du dispatch, nulle hors sonde. */
C56_TASK_TRACE <- false;
C56_LOOP_TICK_COUNT <- 0;
/* C56 : cumul des tranches du travailleur actif (trace seulement). */
C56_WORKER_ACC <- null;
/* C50 : Sonde chronologique legere (tresorerie, profit par ligne, projets batis et refuses). */
C50_CHRONOLOGY_PROBE <- false;
/* C63+C58 : ledger annuel depenses / recettes / occasions. Nul hors sonde. */
C63_INVEST_PROBE <- false;
C63_INVEST_LEDGER <- null;
/* C70 : facteur realise/predit par mode, recalcule au rapport annuel. 1.0 hors reglage. */
C70_MODE_CALIBRATION <- false;
C70_MODE_FACTOR <- { rail = 1.0, road = 1.0, air = 1.0, water = 1.0 };
/* C82 : facteur realise/predit par moteur d'avion, recalcule au rapport annuel. 1.0 hors reglage ou si absent. */
C82_ENGINE_CALIBRATION <- false;
/* C70 ou C82 : score sur le profit calibre. Calcule une fois dans OpexLoadSettings pour que la
 * boucle de selection ne lise qu'une globale, comme avant C82 (meme cadence VM). */
C70_PROFIT_CALIBRATED <- false;
C82_ENGINE_FACTOR <- {};
C82_CHOICE_CALLS <- 0;
C82_CHOICE_DIFFER <- 0;
/* C69 etape 1 : sonde passive goulot de decision P / max(C, F*tau). */
/* Annee de depart de la compagnie (sauvegardee via _startYear) : base des calculs C69/C75 de F et
 * de tau. 1970 n'est qu'un repli, pose avant Start(). */
OPEX_START_YEAR <- 1970;
C69_BOTTLENECK_PROBE <- false;
/* C69 etape 2 : levier. C69_TRACK_BUILDS = sonde ou levier : tau exige les dates de chantier. */
C69_DECISION_BOTTLENECK <- false;
C69_FLEET_EXEMPT <- false;
C69_FLEET_DEMAND_BATCH <- false;
C69_TRACK_BUILDS <- false;
C69_BUILD_DATES <- null;
C69_PENDING_FOLLOWUPS <- null;
C69_BUILD_PASS_COUNT <- 0;
C69_LAST_AFFORDABLE <- null;
C69_LAST_KDEC_DATA <- null;
/* C72 : sonde passive du choix d'avion (C69 etape 1) */
C69_CACHED_KDEC_DATE <- -1;
C69_CACHED_KDEC_VALUE <- 0;
C69_PLANE_CHOICE_CALLS <- 0;
C69_PLANE_CHOICE_DIFFER_ROI <- 0;
C69_PLANE_CHOICE_DIFFER_C69 <- 0;
/* C73 : sonde passive du vivier avant selection et des passes du portefeuille */
C73_VIVIER_LEDGER <- null;
/* C72 etape 2 : levier du choix d'avion (0 = profit max, 1 = ROI max, 2 = P/max(C, K_dec)) */
C72_PLANE_CHOICE <- 0;
/* C84 : profondeur cible de flotte pour l'appareil deja choisi par la politique courante.
 * La ligne reste lancee avec un seul avion sous FLEET_PORTFOLIO ; la cible ne peut assouplir
 * qu'un premier mauvais exercice, et seulement derriere l'attente reelle et le plafond de cadence. */
C84_AIR_TARGET_FLEET <- false;
/* C85 : reduire le choix C68 par route aux avions structurellement non domines,
 * calcules une fois au refresh du catalogue. Experimental, defaut 0. */
C85_AIR_EQUIPMENT_FRONTIER <- false;
/* C75 : plusieurs chantiers par passe en phase riche tant que Capital < K_pass et Capital <= Disponible. */
C75_MULTI_BUILD <- false;
C75_TRACK_PASSES <- false;
C75_PASS_DATES <- null;
C75_YEAR_LEDGER <- null;
/* C76 : sonde passive de la regeneration du vivier sous C39_INVALIDATION_PROBE */
C76_PREV_STATE <- null;
C76_YEAR_LEDGER <- null;
C76_EVENTS_SINCE_PREV <- null;
/* C76 etape 2 / C80 tranche 3 : regeneration du vivier pilotee par les invalidations.
 * 0 = regeneration mensuelle systematique historique (defaut), 1 = regeneration ciblee. */
C76_REGEN_TARGETED <- false;
/* C78 : sonde passive de la fenetre entre le premier et le second aeroport adverse d'une ville.
 * Opex publie son vivier AIR a chaque passage projects ; le harnais shared fournit les build_date AAA. */
C78_SLOT_INTERCEPT_PROBE <- false;
C78_SLOT_PASS_COUNTER <- 0;

/* Tunnel mensuel candidats/acceptes/finances/tentes/construits. Defaut 0 : un AILog
 * par passe projects, sans changer la selection. */
MONTHLY_FUNNEL <- false;
C50_REFUSE_CACHE <- {};
C50_NON_EXPANSION_LEDGER <- null;
/* B3 : test du plafond routier remis à l'échelle par le temps passé à quai. Défaut 0 tant que
 * le banc apparié n'a pas justifié une adoption. Le fret reste sur la borne historique. */
ROAD_TIME_SCALED_CAP <- false;
/* C50b : test causal du seuil de backlog avant doublement d'une ligne rail existante. */
/* air_fleet_probe : _resizeAirFleets n'emet que ses SUCCES (FG|). Quand une ligne aerienne
 * n'grandit pas, la cause est invisible. FR| donne le premier refus rencontre, une fois par ligne
 * et par an. */
AIR_FLEET_PROBE <- false;
/* Sonde de tension : aucun calcul ni journal supplementaire sur le chemin par defaut. */
TENSION_PROBE <- false;
/* Garde unique du logger de portefeuille : evite un OR supplementaire dans le chemin chaud. */
PORTFOLIO_LOG <- false;
/* C45 : persistance complete de l'etat de decision. Defaut aligne sur info.nut (custom_value = 1),
 * adopte au banc officiel 20x10 apparie -- les vingt graines identiques au bit pres. */
SAVE_FULL_STATE <- true;
/* C34.1 : construction aerienne arbitree par le portefeuille seul (1) au lieu de la tache dediee. */
AIR_PORTFOLIO <- true;
/* C34.2 : croissance de flotte aerienne arbitree par le portefeuille (1) au lieu de la tache dediee. */
FLEET_PORTFOLIO <- true;
/* C32 : bonus forfaitaires de classement du fret. 0 = supprimes. */
/* Devis réel par AITestMode + AIAccounting avant engagement (docs/taches.md C7). */
RAIL_DEVIS <- true;
/* Expansion marginale : bras A/B inerte par defaut jusqu'au verdict du banc. */
RAIL_EXPAND <- false;
/* F-RAIL-ECON-01 : prise en compte du cout du depot dans le capital d'infrastructure rail. */
RAIL_DEPOT_COST <- false;
OPS_PER_TICK <- 10000;
_budgetSignIds <- {};
_currentTaskName <- null;
_currentTaskLogged <- false;
/* Reserve de tresorerie dynamique : adaptee a la taille de la flotte pour liberer le capital
 * des les premieres annees (15 000 £ au lieu de 50 000 £) et eviter les soldes oisifs. */
DYNAMIC_CASH_RESERVE <- true;
/* P1 : repli empirique du filtre de financabilite. Le facteur rail 1,7
 * reste applique au capital de construction estime ; les autres modes restent a 1,0. */
CAPITAL_CALIBRATION <- true;
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
/* Preserve NoAI suspend cadence after pruning false-only AIR branches. */
OPEX_AIR_CAP_PAD <- false;
OPEX_AIR_PLAN_PAD <- false;
/* C15 : cadence minimale d'agrandissement de flotte en jours (7 = hebdomadaire, 365 = defaut annuel historique). */
AIR_FLEET_CADENCE_DAYS <- 7;
/* C14 : tampon de cargo au sol pour achat proportionnel (-1 = inactif/defaut). */
AIR_FLEET_BUFFER <- -1;
PAX_FULL_LOAD <- true;
AIR_FULL_LOAD <- 0;
C53_ORDER_NONSTOP <- false;
C53_ORDER_NOLOAD <- false;
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
 * Ce correctif reste desactive : il empile jusqu'a 16 camions sur des arrets a 1 seul quai. */
ROAD_LOADING_FIX <- false;
/* C52 : symbole de compatibilite. Le remappage ET_VEHICLE_AUTOREPLACED est maintenant
 * inconditionnel ; le reglage homonyme est deprecated et sa valeur est ignoree. */
EVENT_VEHICLE_AUTOREPLACED <- true;
/* C52 : sonde annuelle des remappages; le ledger reste nul hors sonde. */
C52_AUTOREPLACE_LOG <- false;
C52_AUTOREPLACE_LEDGER <- null;
/* C52 : sonde passive de frequence des evenements. Le ledger reste nul hors sonde. */
C52_EVENT_EXPOSURE_PROBE <- false;
C52_EVENT_EXPOSURE_LEDGER <- null;
/* C52 #2 : reaction et reconstitution sur tout crash de vehicule */
EVENT_VEHICLE_CRASHED <- false;
C52_CRASH_LOG <- false;
/* C52 #4 : reaction aux vehicules non rentables chroniques */
EVENT_VEHICLE_UNPROFITABLE <- false;
UNPROFITABLE_STREAK_THRESHOLD <- 3;
C52_UNPROFITABLE_LOG <- false;
/* C52 #7 : sonde ET_STATION_FIRST_VEHICLE */
C52_STATION_FIRST_VEHICLE_LOG <- false;
/* P3 / A7.5 : une nouvelle ville ou industrie rend le portefeuille obsolete.
 * Le rafraichissement reactif est rare et evite d'attendre le prochain mois. */
EVENT_CATALOG_INVALIDATE <- true;
/* C43/E3 famille 2 : CASH_RESERVE_MIN mord-il ? OpexCashReserve() est appelee tres souvent (a
 * chaque decision de construction), donc journaliser chaque appel serait bruyant -- compteurs
 * cumulatifs, publies une fois par an en delta par la tache "report". */
CASH_RESERVE_PROBE <- false;
CASH_RESERVE_PROBE_CALLS <- 0;
CASH_RESERVE_PROBE_MIN_BINDS <- 0;
CASH_RESERVE_PROBE_MAX_BINDS <- 0;
/* Plafond absolu du pathfinder. Initialisation de repli seulement : Start() le remplace UNE fois
 * par pathfinder_hard_cap_k. Plafonné à 10 000 (docs/taches.md A3, §0 undecies ter) pour
 * éliminer le gel de l'IA pendant des mois sur les recherches chères. */
HARD_ITERATION_CAP <- 10000;

/* C80 tranche 0 : socle de l'orchestrateur à double registre (intentions / exécution).
 * 0 = ordonnanceur historique (défaut), 1 = orchestrateur à double registre actif. */
C80_DOUBLE_REGISTER <- false;

/* C80 tranche 1 : migration de la recherche A* rail (_railSearch) dans le registre d'exécution.
 * 0 = désactivé (défaut), 1 = travailleur "rail_search" actif sous c80_double_register=1. */
C80_WORKER_RAIL <- false;

/* C80 tranche 2 : découpage de la croissance urbaine (_tryTownGrowth) en travailleur "town_growth".
 * 0 = désactivé (défaut), 1 = travailleur "town_growth" actif sous c80_double_register=1. */
C80_WORKER_TOWN <- false;

/* C76 : sous C76_REGEN_TARGETED, evite les regenerations completes du vivier pour
 * les variations de budget seul et traite localement les lignes et subventions. 0 = desactive (defaut). */
C76_LEAN_INVALIDATION <- false;

/* C76 : sous C76_REGEN_TARGETED, un mois sans regeneration complete fait quand meme tourner le
 * cargo fret (regeneration des seuls modes rail et route sur le cargo suivant). Sans lui, le lot
 * fret reste fige entre deux regenerations completes. 0 = desactive (defaut). */
C76_FREIGHT_ROTATION <- false;

/* C80 tranche 4 : sous C76, une couche industries ou moteurs non aeriens ne regenere que les
 * modes qui en dependent (rail, route, eau) au lieu du vivier entier. 0 = desactive (defaut). */
C80_MODE_REGEN <- false;

/* C80 tranche 5 : memo de l'avion choisi par route aerienne. Rempli par la generation complete
 * (etat 1), relu par les mises a jour apres chantier (etat 2) qui ne recalculent que l'economie
 * de l'avion memorise. Cache reconstructible, non sauvegarde : vide apres chargement. */
C80_AIR_CHOICE_MEMO <- false;
AIR_CHOICE_MEMO <- {};
AIR_CHOICE_MEMO_STATE <- 0;
/* C80 tranche 5 bis : index exacts des routes aeriennes par gare et des paires reliees.
 * Defaut 1 depuis le 2026-09-23 (decision utilisateur) : memes decisions, ~1/3 d'opcodes hub-hub
 * en moins, 20x10 neutre ; valeur reelle lue dans settings.nut. */
C80_AIR_HUB_INDEX <- false;

/* C80 tâche 5 : filtre de valeur des projets marginaux (chantiers secondaires sous multi-build).
 * 0 = désactivé (défaut), 1 = filtre actif selon le profit par véhicule réalisé du mode. */
C80_MARGINAL_FLOOR <- false;
C80_MARGINAL_FLOOR_LEDGER <- null;

/* C80 air eval fast : optimisations exactes de la planification aerienne (memo d'economie,
 * memo de trajectoire/revenu, report de GetOrderDistance). Defaut 0. */
C80_AIR_EVAL_FAST <- false;
AIR_ECONOMICS_MEMO <- {};
AIR_TRIP_MEMO <- {};
AIR_MEMO_MONTH <- -1;

/* Sonde incrementale air sous probe_portfolio */
C80_AIR_INC_COUNTS <- { full = 0, targeted = 0, none = 0 };

/* C78 etape 2 : annee de la derniere generation aerienne journalisee par la sonde C78 etape 2. */
C78_GEN_LOG_YEAR <- -1;

/* C86 Variante A : prise en compte de la cannibalisation hub->hub en retranchant
 * la perte de revenu des lignes existantes des deux hubs. 0 = desactive (defaut). */
AIR_HUBHUB_MARGINAL <- false;

/* C86 Variante B : plafond abaisse de routes par aeroport hub.
 * 0 = plafonds actuels (4 petits/commuter, 12 grands), 1..12 = min(plafond actuel, N). */
AIR_HUB_MAX_ROUTES <- 0;
