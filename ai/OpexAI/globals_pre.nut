/* C65 passe 2 : globales du bloc AVANT require(budget/catalog/...). */
/* Declare avant les require() : catalog.nut consulte ce drapeau dans son cycle annuel. Repli
 * actif jusqu'a la lecture unique de road_mode dans Start(), comme les autres reglages de
 * decision. Le defaut vrai est celui de info.nut ; 0 reconstitue la baseline sans route, dont le
 * chemin d'opcodes reste alors EXACTEMENT celui des campagnes anterieures. */
ROAD_BUILD_ENABLED <- true;
/* V166 : interrupteurs de mode (bancs mono-mode, rail contre rail, air contre air). Un mode a faux
 * ne genere ni candidat ni balayage de catalogue et ne construit rien ; les quatre a vrai = defaut. */
MODE_AIR <- true;
MODE_RAIL <- true;
MODE_ROAD <- true;
MODE_WATER <- true;
/* V168 : borne de distance des candidats rail. 160 = defaut (portes A et B du 13/10) ; 0 = derivee
 * du plafond d'A* par la table de noeuds (94 tuiles a 10k) ; N = N tuiles, sans le filtre
 * d'iterations predites. */
V168_RAIL_MAX_DIST <- 160;
V177_RAIL_PAX_MIN_DIST <- 0;
V182_RAIL_FREIGHT_MIN_DIST <- 0;
/* V264 : fret convergent vers une industrie deja desservie. Defaut vrai depuis le 19/10 (40x10 PC
 * +111,8 k/an sur 39 paires, accepte par derogation utilisateur). 0 = aucun calcul du mecanisme. */
V264_CONVERGENT_FREIGHT <- true;
/* V269 : relachement tardif du vivier rail (orchestrator.nut, _v217RailRefill). 0 = inerte,
 * N = annees apres le depart (defaut 5 depuis le 20/10, decision utilisateur apres le 40x10
 * GitHub +83,1 k, 24/16, IC95 [-8 k ; +174 k]). Quand le vivier est vide et la caisse oisive,
 * la regeneration V217 accepte le fret jusqu'a V269_RAIL_MAX_DIST tuiles. */
V269_RAIL_LATE_RELAX <- 5;
V269_RAIL_MAX_DIST <- 250;
V269_IDLE_CASH_MIN <- 1000000;
V269_RELAXED <- false;
V269_ON <- false;
/* V195 : V182 limite aux N premieres annees (0 = toujours). */
V195_V182_YEARS <- 0;
/* V186 : tranches A* rail avancees par passage de file (1..16, defaut 1 = historique). */
const V186_RAIL_SEARCH_SLICES = 1;
/* V190 : lignes rail fret posees en double voie a sens unique des la construction. */
V190_RAIL_DOUBLE_BUILD <- false;
/* V197 : double voie guidee (outwardSide pour voie 1, guideTiles pour voie 2). */
V197_GUIDED_DOUBLE <- false;
/* V198 : double voie par gabarits de gare (boucle source + gare traversante destination). */
V198_TEMPLATE_DOUBLE <- false;
V200_DOUBLE_CASH_K <- 0;
/* V199 : robustesse de pose rail a la maniere d'AAAHogEx (reprise locale, nivellement homeward, signaux en ligne, demolition). */
V199_ROBUST_BUILD <- false;
V199_LEVEL_BUDGET_K <- 20;
/* V207 : part de captage des passagers urbains par le rail (0 = historique 22 %). */
V207_RAIL_PAX_SHARE_PCT <- 0;
/* V207 : second cargo courrier sur les rames passagers rail. */
V207_RAIL_MAIL <- false;
/* V207 : nombre maximal d'arrets de bus traversants joints a chaque gare rail passagers. */
V207_RAIL_PAX_JOINED_STOPS <- 0;
/* V207 : sites de gare passagers classes par production captee (0 = premiers sites trouves). */
V207_RAIL_PAX_SITE_RANK_PCT <- 0;
/* V212 : calibration du revenu et du capital predits des lignes rail passagers (100 = inerte).
 * Porte A V207 (40x3) : profit realise/predit 1,23-1,58 en pax contre 0,86 en fret, capital
 * reel/modele 0,84 en pax contre 1,28 en fret. Qualifie en rail seul (150/85 avec V207, 15/10) mais
 * perdant en partie complete (16/10 : -244 k/an, p=0,027, l'aerien recule de 20 %) : defaut 100. */
V212_RAIL_PAX_REVENUE_PCT <- 100;
V212_RAIL_PAX_CAPITAL_PCT <- 100;
/* V275 : masque rail voyageurs en multimodal (voir info.nut). */
V275_RAIL_PAX_MM <- 15;
/* V214 : couts de virage du A* rail a la AAAHogEx (pathfinder.nut, InitializeParameters/__Cost).
 * Defaut 300/1500 adopte sur decision utilisateur le 16/10 apres B 20x10 positif,
 * avec portes A 40x3 et 40x5 non qualifiees. 0 = historique (50 a chaque changement de direction,
 * aucun surcout de coude serre).
 * V214_RAIL_TURN_COST > 0 : entrer dans une diagonale est gratuit, en sortir coute ce montant.
 * V214_RAIL_TIGHT_TURN_COST > 0 : coude de 90 degres pris sur une seule tuile (droite, coin,
 * droite perpendiculaire), 88 km/h en acceleration realiste ; ramene a 100 sous 40 tuiles. */
V214_RAIL_TURN_COST <- 300;
V214_RAIL_TIGHT_TURN_COST <- 1500;
function OpexV207Active()
{
  return V207_RAIL_MAIL || V207_RAIL_PAX_SHARE_PCT > 0 || V207_RAIL_PAX_JOINED_STOPS > 0;
}
/* V190 : annee a partir de laquelle la double voie est posee (annee de depart + delai). */
V190_FROM_YEAR <- 0;
function OpexV190Active()
{
  if (!V190_RAIL_DOUBLE_BUILD || AIDate.GetYear(AIDate.GetCurrentDate()) < V190_FROM_YEAR) return false;
  /* V200 : toute la machinerie double (plans a deux quais, seconde voie, gabarits) n'est
   * active que si la caisse depasse le seuil ; sinon la ligne suit le chemin simple d'origine. */
  if (V200_DOUBLE_CASH_K > 0 && AICompany.GetBankBalance(AICompany.COMPANY_SELF) - AICompany.GetLoanAmount() < V200_DOUBLE_CASH_K * 1000) return false;
  return true;
}
function OpexV198Active()
{
  return V198_TEMPLATE_DOUBLE && OpexV190Active();
}
V190_RAIL_MAX_TRAINS <- 4;
/* V172 : heuristique A* rail renforcee sur longues distances (>= v172_rail_long_weight_dist).
 * 0 = inerte (poids V91_ASTAR_WEIGHT_PCT conserve, defaut) ; 100..300 = poids applique. */
V172_RAIL_LONG_WEIGHT_PCT <- 200;
V216_PROBE <- false;
V211_RIVALS <- false;
V211_LAST_QUARTER <- -1;
/* V262 T10/T15 : annee et date du dernier releve orphelins. Non persistes
 * (un rechargement un 1er decembre peut journaliser une seconde fois).
 * Aucune decision ne lit ces valeurs. */
V262_ORPHAN_YEAR <- -1;
V262_ORPHAN_DATE <- -1;
/* V216a : 0 inerte, 1 gain net de la compagnie, 2 part de la ligne (probe_v216.nut). */
V216A_GHOST_DEMAND <- 0;
/* V216f : sejour mecanique en gare dans le cycle rail, en % de l'estimation EST-16 (economy.nut). */
V216F_DWELL_PCT <- 0;
/* V249 : statue quand on est riche, sans seuil en livres (task_v249.nut). */
V249_STATUE <- 0;
/* Vrai si une passe projets s'est arretee faute de caisse depuis le dernier
 * passage statue. Vrai au depart : le premier mois ne compte pas. Pas sauvegarde. */
V249_CASH_STOP <- true;
/* Vrai si une passe projets s'est arretee faute de caisse depuis le dernier
 * passage de rafraichissement aerien. Vrai au depart. Pas sauvegarde. */
V252_CASH_STOP <- true;
/* V250 : 0 inerte, 1 droits en ville disputee, 2 test de creneau aeroport,
 * 3 test elargi a toutes les villes ou un rival a un aeroport. */
V250_RIGHTS <- 0;
/* Meme signal que V249, mais reserve au mode 1. Le mode 2 ne le lit pas.
 * Vrai au depart : le premier mois de mode 1 ne compte pas. Pas sauvegarde. */
V250_CASH_STOP <- true;
/* V259 : renouvellement des ponts plus rapides (task_v259.nut). */
V259_BRIDGE_RENEW <- 0;
/* V277 : publication rapide des projets air et filtre indexe de re-selection. */
V277_AIR_PUB_FAST <- 0;
V172_RAIL_LONG_WEIGHT_DIST <- 100;
/* Cascade pax par distance decroissante : air seul, air+rail, rail seul,
 * route seule. Le fret accompagne la premiere passe. */
STAGED_BOOTSTRAP <- true;
/* D4 : Dwell time de chargement/dechargement a la station pour les bus passagers (jours) */
const ROAD_PAX_STOP_DWELL_DAYS = 6;
/* D4, extension aerienne : le diagnostic 10 ans x 5 graines
 * (results/diag_road_purpose.json) donne revenu reel/predit median = 1,0427 pour
 * air|pax. Le modele etait donc legerement conservateur. Ce facteur ne touche
 * que le revenu passager aerien, avant le calcul du profit et des scores. */
AIR_PAX_REVENUE_CALIBRATION_PCT <- 104;
/* C27 : Sortir les bonus du numerateur de densite du portefeuille (adopte) */
/* Panneaux de diagnostic : lu UNE fois depuis le reglage dans Start(), pas a chaque appel (57
 * panneaux par an, GetSetting a chaque fois serait du gaspillage d'opcodes pour une valeur qui ne
 * change jamais en cours de partie). Defaut vrai : voir info.nut::debug_signs -- toute
 * l'instrumentation de sweeps/*.py passe par ces panneaux, AILog.Info n'etant pas capture par
 * OpenTTDLab. On ne les coupe que pour une partie avec des humains. */
DEBUG_SIGNS <- true;
/* V167 : masque du reglage `probes` apres expansion du bit 1 (voir settings.nut). */
OPEX_PROBE_MASK <- 2;
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
/* B9/G4 : sonde passive post-chantier du catchment AIR. Defaut 0 : aucune tuile
 * supplementaire n'est inspectee dans le comportement livre. */
AIR_CATCHMENT_PROBE <- false;
/* M3/G12 : sonde passive du choix de materiel avant ROI. Elle n'est jamais lue par les
 * regles de selection ; elle autorise uniquement les comparatifs et logs de diagnostic. */
EQUIPMENT_ROI_PROBE <- false;
/* Nombre maximal d'arrets bus annexes partageant directement le StationID de l'aeroport. */
AIR_JOINED_STOP_LIMIT <- 2;
/* Early-slot: prioritise profitable air projects that claim a first
 * airport in large towns before competitors can consume both town slots. */
AIR_EARLY_SLOT_TARGET_TOWNS <- 6;
AIR_EARLY_SLOT_MIN_POP <- 1000;
AIR_EARLY_SLOT_BONUS_PCT <- 50;
/* C83.1 : objectif territorial distinct du bonus early-slot historique.
 * L'ablation du 2026-09-24 a teste 24 villes, mais les 18 villes marginales
 * ajoutaient des courses moins propres et degradaient la valeur au 5x6 ;
 * conserver le coeur des 6 plus grandes villes tant qu'un elargissement n'est
 * pas requalifie. */
AIR_C83_TARGET_TOWNS <- 6;
/* C83 : revalider les sites connus ; chercher seulement dans la ville cible.
 * Intervention comportementale experimentale, ancien parcours conserve a 0. */
C83_LOCAL_REPAIR <- false;
/* C83 revue : paquet mesurable. 0 laisse le chemin de decision courant ; seul le test
 * du drapeau s'ajoute. Les sondes restent gatees par leurs flags existants. */
C83_FIXES <- false;
/* C83 : une seule grande ville encore vide (deux slots libres), avant que le
 * maillage ne se fige. 0 = aucun effet. La cible et l'arret sont des globales
 * restaurees apres Load quand le reglage est arme. */
C83_PREEMPT_OPEN <- false;
C83_PREEMPT_TOWN <- -1;
C83_PREEMPT_STOPPED <- false;
/* Refaire le sac a dos contre la caisse vivante, sans repayer la generation des candidats. */
/* C36.1 : Caching incremental du vivier post-chantier. */
/* Compatibilite de cadence VM apres suppression des flags economy morts. Constante interne, jamais configurable ni vraie. */
OPEX_ECONOMY_OPCODE_COMPAT_FALSE <- false;
/* C39.0 : sonde passive du bus d'invalidation. A 1, les evenements marquent les
 * dependances qui SERAIENT rafraichies et journalisent la passe mensuelle actuelle ;
 * ils ne changent ni sa cadence, ni les candidats, ni les decisions. */
C39_INVALIDATION_PROBE <- false;
/* C39.3 : sonde de l'effet réel d'une invalidation sur le catalogue et le premier projet. */
C39_DECISION_DELTA_PROBE <- false;
/* C39.4 : explique pourquoi un EngineAvailable air n'est pas retenu par les combos. */
C39_AIR_REASON_PROBE <- false;
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
/* V95 item 1 : tours de file selectionnes vs no-op, strictement observatoire.
 * Meme gate que les ledgers C41/C39 : probe_scheduler, defaut 0. Aucune admission. */
V95_SCHED_IDLE_LEDGER <- false;
/* C41.16 : ventilation passive de la generation de candidats route historique. */
C41_ROAD_CANDIDATE_PROFILE <- false;
/* C41.17 : sous-ventilation passive du fret producteur->accepteur. */
C41_ROAD_FREIGHT_PROFILE <- false;
/* C41.18 : index spatial local des origines fret route deja desservies. */
/* C41.19 : profil passif interne des puits urbains du fret route. */
C41_ROAD_FREIGHT_TOWN_PROFILE <- false;
/* C41.20 : index experimental des puits urbains acceptant le cargo fret. */
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
C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE <- false;
C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE <- false;
C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE <- false;
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
/* C70 : facteur realise/predit par mode, recalcule au rapport annuel et au rechargement. */
C70_MODE_FACTOR <- { rail = 1.0, road = 1.0, air = 1.0, water = 1.0 };
/* C69 etape 1 : sonde passive goulot de decision P / max(C, F*tau). */
/* Annee de depart de la compagnie (sauvegardee via _startYear) : base des calculs C69/C75 de F et
 * de tau. 1970 n'est qu'un repli, pose avant Start(). */
OPEX_START_YEAR <- 1970;
C69_BOTTLENECK_PROBE <- false;
/* C69 : le levier permanent exige le suivi des dates de chantier pour tau. */
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
/* V93 fige : pas de plancher a 600 habitants pour poser un aeroport.
 * Le plancher minimal n'est pas un reglage : il evite seulement les hameaux. */
V93_AIRPORT_MIN_POP <- 100;
V95_AIR_POST73_YEAR <- -1;
/* V134 : second aeroport point-a-point (newpair) vers une ville libre pour une
 * ville dont l'aeroport existant a atteint AIR_HUB_MAX_ROUTES et qui ouvre un
 * second slot. Defaut 0 : filtre origin_served historique intact. */
V134_AIR_P2P_SATURATED_HUB <- false;
/* V133 : quarantaine de ville apres echec physique d'aeroport, et salvage
 * des paires du lot qui ne dependent pas du site fautif. Defaut 0 : aucun
 * ecart, aucune ecriture de table, aucun journal. La duree est 730 jours
 * de jeu, ecrite au moment du marquage. V133_AIR_QUARANTINE : townId -> date
 * de fin (entier). V133_AIR_BATCH_FAILED : villes fautives de la passe
 * courante. V133_AIR_SKIP_LOGGED : anti-doublon du journal V133_SKIP en
 * construction. V133_AIR_LAST_SITE_ERROR : dernier code du test de site,
 * lu seulement si le reglage est actif. */
V133_AIR_BUILD_RETRY <- false;
V278_AIR_LAZY_SITES <- false;
V278_AIR_VALIDITY <- null;
V278_AIR_EPOCH <- 0;
V133_AIR_QUARANTINE <- {};
V133_AIR_BATCH_FAILED <- {};
V133_AIR_SKIP_LOGGED <- {};
V133_AIR_LAST_SITE_ERROR <- 0;
/* Devis de terrassement pour la sonde probe_air_finance_margin seulement.
 * N'entre ni dans le capital C121 ni dans la marge de caisse.
 * V126_JOINED_STOP_COST : cout modelise d'UN arret joint, journalise par la sonde.
 * AIR_SITE_COST_QUOTES : cache reconstructible par ancre et type, jamais sauvegarde. */
V126_JOINED_STOP_COST <- 300;
AIR_SITE_COST_QUOTES <- {};
C96_AIR_SITE_MAX_VALID <- 4;
C96_AIR_SITE_EXTRA_RINGS <- 1;
C117_AIR_SAMPLE_DAYS <- 2;
C117_AIR_LAST_DATE <- -1;
C117_AIR_LINE_STATE <- {};
C117_AIR_VEHICLE_STATE <- {};
C121_STATION_FLUX_LAST_DATE <- -1;
C121_STATION_FLUX_STATE <- {};
/* Etat transitoire « avion de la partie » par type d'aeroport. Non
 * sauvegarde : apres chargement, l'etat se reconstruit tout seul.
 * Une cle de mode (capital, profit par vehicule) pourra s'y ajouter plus tard. */
C121_GAME_ENGINE_STATE <- {};
C121_AIR_PROJECT_REALIZATION_ADAPTIVE <- false;
C121_AIR_PROJECT_REALIZATION_MIN_CONTESTABLE_PERMILLE <- 650;
C121_AIR_PROJECT_REALIZATION_MAX_OPEN_PERMILLE <- 200;
C121_AIR_PROJECT_REALIZATION_MIN_PRESSURED <- 3;
C121_AIR_PROJECT_REALIZATION_CLASSIFY_YEARS <- 2;
C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED <- 0;
/* -1 = observation/non classe, 0 = race, 1 = efficiency. Une fois classe,
 * le regime reste stable pour eviter qu'une politique modifie son propre
 * signal de classification. */
C121_AIR_PROJECT_REALIZATION_REGIME <- -1;
C121_AIR_PRESSURE_SNAPSHOT <- null;
C121_AIR_PRESSURE_ACCUM <- null;
C121_AIR_PRESSURE_PREV <- null;
C122_AIR_REGIME_SHADOW <- false;
/* C122.4 : sonde locale de menace territoriale. Elle ne cree aucune politique :
 * elle relie seulement une transition C83 remaining=1 a un projet AIR deja
 * vivant/finance, puis suit le meme TownID jusqu'a claimed/lost. */
C122_AIR_THREAT_PROBE <- false;
C122_AIR_THREAT_WATCH <- {};
C122_AIR_THREAT_SEQ <- 0;
C122_AIR_THREAT_RETRY <- false;
C122_AIR_THREAT_RETRY_COUNT <- 0;
C121_AIR_ENGINE_CAPACITY_OBS <- {};
/* C121 : calibration recente du revenu des NOUVELLES lignes, par bras. Le
 * cold-start reste 1.0. Le rapport annuel remplace ensuite cette valeur par une
 * moyenne recente realise/brut, lisible en O(1) pendant le scoring. */
C121_AIR_REALIZATION_FACTOR <- { newpair = 1.0, hubsite = 1.0, hubhub = 1.0 };
C121_AIR_REALIZATION_MIN_LINES <- 2;
/* Cache transitoire reconstruit au rapport annuel et apres Load. */
AIR_P0_DIRECT_REALIZATION_ACTIVE <- false;
C121_AIR_P0_DIRECT_FACTOR <- { hubsite = 1.0, hubhub = 1.0 };
/* Diagnostic agrege de cout du chemin causal C121 pendant une passe AIR.
 * La table est recreee a chaque planification (ou conservee dans resumeState
 * pour une passe slicee) et ne participe a aucune decision. */
C121_AIR_PLAN_PERF <- null;
/* Sonde probe_loop_ops : agregats annuels d'opcodes de la boucle principale (diagnostic). */
PROBE_LOOP_OPS <- false;
/* Sonde probe_span_trace : intervalles dates des micro-taches. Defaut 0, aucun effet. */
PROBE_SPAN_TRACE <- false;
/* F-EVENT-BACKLOG-01 : sonde passive de la file d'evenements. Defaut 0. */
PROBE_EVENT_BACKLOG <- false;
/* Sonde de rejet de selection portefeuille AIR (cash, floor, dedupe, topk). Defaut 0. */
PROBE_SELECT_REJECT <- false;
EVENT_BACKLOG_CALLS <- 0;
EVENT_BACKLOG_EVENTS <- 0;
EVENT_BACKLOG_MAX_BURST <- 0;
EVENT_BACKLOG_OPS_TOTAL <- 0;
EVENT_BACKLOG_OPS_MAX <- 0;
EVENT_BACKLOG_MONTH <- -1;
SPAN_STACK <- null;
SPAN_BY_ID <- null;
SPAN_NEXT_ID <- 1;
SPAN_LINES <- 0;
SPAN_AGG_LINES <- 0;
SPAN_YEAR <- -1;
SPAN_ROOT_AGG <- null;
OPEX_LOOP_PROF <- null;
OPEX_LOOP_PROF_YEAR <- -1;
OPEX_LOOP_PROF_TICK0 <- 0;
/* Chemins opcode exacts : defaut historique. Le mode check compare et garde l'ancien resultat. */
OPCODE_EXACT_STATS <- null;
OPCODE_EXACT_BREAK <- null;
OPCODE_EXACT_MISMATCHES <- null;
OPCODE_EXACT_CAL_YEAR <- -1;
OPCODE_EXACT_LATE_DATE <- -1;
OPCODE_EXACT_SITE_NAME <- null;
OPCODE_EXACT_PLAN_ONCE <- null;
CATALOG_COST_ACTIVE <- null;
C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <- 0;
C121_AIR_FIRST_LIVE_STATE <- {};
C121_AIR_FIRST_LIVE_OPS <- 0;
C121_AIR_FIRST_LIVE_SAMPLES <- 0;
C121_AIR_FIRST_LIVE_PRIORITY_STATE <- {};
C121_CATALOG_FIRST_YEAR_ACTIVE <- false;
/* Derive du monde, volontairement absent de Save(). */
C121_CATALOG_CACHE <- {};
C121_CATALOG_AIRPORT_PRICES <- {};
C121_CATALOG_AIRPORT_REV <- {};
C121_CATALOG_STATION_REV <- {};
C121_CATALOG_STATION_LINES <- {};
C121_CATALOG_HUB_LEARN_REV <- {};
C121_CATALOG_AIRPORT_LEARN_REV <- {};
C121_CATALOG_ARM_LEARN_REV <- {};
C121_CATALOG_TOWN_PRIORITY <- {};
C121_CATALOG_TOWN_REV <- {};
C121_CATALOG_TOWN_POP <- {};
C121_CATALOG_TOWN_PROD <- {};
C121_CATALOG_TOWN_CURSOR <- 0;
C121_CATALOG_TOWN_BATCH_DATE <- -1;
/* Snapshot endpoint C121 limite a une passe de planification AIR. Un meme site
 * (ancre/type/cargo/etat de reutilisation) est evalue une fois puis reutilise
 * pour toutes les paires de cette passe. */
C121_AIR_ENDPOINT_CACHE <- null;
/* C121 timing adaptatif : chaque station publie une moyenne du residu
 * operationnel observe sur une fenetre recente d'environ un trimestre.
 * Le residu reste signe pendant l'accumulation pour ne pas biaiser la
 * quantification de C117 (echantillonnage tous les 2 jours) ; seule
 * l'estimation publiee, interpretee comme un delai, est bornee a >= 0. */
C121_AIR_HUB_DELAY_STATE <- {};
C121_AIR_HUB_DELAY_WINDOW_DAYS <- 91;
C121_AIR_HUB_DELAY_MIN_OBS <- 2;
C121_AIR_HUB_DELAY_UPDATE_OPS <- 0;
C121_AIR_HUB_DELAY_UPDATE_SAMPLES <- 0;
/* C116.2 : snapshot tres bon marche du portefeuille AIR deja classe. Il est
 * rempli uniquement pour la sonde C116 a partir de la
 * liste `affordable` deja triee : aucune recherche de route supplementaire. */
C116_AIR_PROJECT_SNAPSHOT <- null;
/* Cargo passagers retenu pour le catchment de site. -1 tant qu'il n'est pas connu. */
AIR_DEMAND_PAX_CARGO <- -1;
/* C75 : plusieurs chantiers par passe en phase riche tant que Capital < K_pass et Capital <= Disponible. */
/* C75 bis : autorise une seule nouvelle ligne finançable a franchir K_pass par passe. Defaut 0. */
C75_KPASS_BYPASS_LEDGER <- null;
C75_KPASS_BYPASS_LEDGER_YEAR <- -1;
/* Facteur de financement rail applique dans OpexProjectFinanceCapital.
 * Reglage experimental, defaut historique 170. */
RAIL_FINANCE_BIAS_PCT <- 100;
C75_PASS_DATES <- null;
C75_YEAR_LEDGER <- null;
/* C76 : sonde passive de la regeneration du vivier sous C39_INVALIDATION_PROBE */
C76_PREV_STATE <- null;
C76_YEAR_LEDGER <- null;
C76_EVENTS_SINCE_PREV <- null;
/* C78 : sonde passive de la fenetre entre le premier et le second aeroport adverse d'une ville.
 * Opex publie son vivier AIR a chaque passage projects ; le harnais shared fournit les build_date AAA. */
C78_SLOT_INTERCEPT_PROBE <- false;
C78_SLOT_PASS_COUNTER <- 0;

/* Tunnel mensuel candidats/acceptes/finances/tentes/construits. Defaut 0 : un AILog
 * par passe projects, sans changer la selection. */
MONTHLY_FUNNEL <- false;
C50_REFUSE_CACHE <- {};
C50_NON_EXPANSION_LEDGER <- null;
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
/* C34.2 : croissance de flotte aerienne arbitree par le portefeuille (1) au lieu de la tache dediee. */
/* C32 : bonus forfaitaires de classement du fret. 0 = supprimes. */
/* Devis réel par AITestMode + AIAccounting avant engagement (docs/taches.md C7). */
/* F-RAIL-ECON-01 : prise en compte du cout du depot dans le capital d'infrastructure rail. */
RAIL_DEPOT_COST <- false;
OPS_PER_TICK <- 10000;
_budgetSignIds <- {};
_currentTaskName <- null;
_currentTaskLogged <- false;
/* Reserve de tresorerie dynamique : adaptee a la taille de la flotte pour liberer le capital
 * des les premieres annees (15 000 £ au lieu de 50 000 £) et eviter les soldes oisifs. */
/* P1 : repli empirique du filtre de financabilite. Le facteur rail 1,7
 * reste applique au capital de construction estime ; les autres modes restent a 1,0. */
/* P4 : n'exclut de la memoire d'abandon que les refus transitoires de caisse
 * (CASH / ERR_NOT_ENOUGH_CASH) survenus apres le garde du portefeuille. Reglage
 * ajoute le 2026-09-08 uniquement pour isoler P4 au banc factoriel P1xP3xP4 sans
 * dupliquer d'arbre Git ; 0 reproduit le comportement historique pre-P4. */
/* docs/taches.md S3 undecies (2026-09-03) : les lignes aeriennes rangent des TUILES d'aeroport
 * dans stationA/stationB, mais le code de hub de builder_air.nut les lisait comme des StationID.
 * Consequence mesuree graine 42 : la garde `alreadyConnected` toujours fausse -> NEUF liaisons sur
 * la meme paire de villes en 3 ans, plafond maxRoutes inoperant, et decote de saturation
 * `/(routes+1)` toujours divisee par 1. 1 = resolution correcte tuile -> StationID ;
 * 0 = comportement casse d'avant le 2026-09-03, pour que le banc puisse chiffrer l'ecart. */
/* C15 : cadence minimale d'agrandissement de flotte en jours (7 = hebdomadaire, 365 = defaut annuel historique). */
AIR_FLEET_CADENCE_DAYS <- 7;
/* V161 : valeur d'un renfort AIR plafonnee par un a priori net des voisines
 * (V161_PRIOR_OWN - V161_PRIOR_NEIGHBOUR x voisines partageant une gare - amortissement).
 * Un renfort reste a sa valeur modele perd l'exemption C70. */
/* Mesure du 12/10 (v160_B20x10, 1973-74) : +13,4 k sur la ligne, -2,6 k par voisine. */
V161_PRIOR_OWN <- 13000;
V161_PRIOR_NEIGHBOUR <- 2600;
/* C14 : tampon de cargo au sol pour achat proportionnel (-1 = inactif/defaut). */
AIR_FLEET_BUFFER <- -1;
/* Bras experimental : reutiliser un aeroport rentable pour une nouvelle destination. */
/* V217 : recharge du vivier rail sur tresorerie oisive (orchestrator.nut). 0 = inerte (defaut),
 * 1 = fret seul, 2 = fret et voyageurs. */
V217_RAIL_REFILL <- 0;
V217_IDLE_CASH_MIN <- 100000;
V217_POOL_MIN <- 2;
V217_LAST_MONTH <- -1;
V217_REGEN_NO_PAX <- false;
AIR0310_SITE_VALIDITY_STATE <- null;
/* E10 : Correctif du doublement de flotte routiere au cycle de construction */
/* C26a : Pricer l'avion de la ligne lors du refleet au lieu du meilleur avion du catalogue */
/* C16 : Plafond physique de flotte aerienne derive de la cadence d'absorption de la piste */
/* C52 : compatibilite ; le remappage ET_VEHICLE_AUTOREPLACED est inconditionnel. */
EVENT_VEHICLE_AUTOREPLACED <- true;
/* C52 : sonde annuelle des remappages; le ledger reste nul hors sonde. */
C52_AUTOREPLACE_LOG <- false;
C52_AUTOREPLACE_LEDGER <- null;
/* C52 : sonde passive de frequence des evenements. Le ledger reste nul hors sonde. */
C52_EVENT_EXPOSURE_PROBE <- false;
C52_EVENT_EXPOSURE_LEDGER <- null;
C52_CRASH_LOG <- false;
C52_UNPROFITABLE_LOG <- false;
/* C52 #7 : sonde ET_STATION_FIRST_VEHICLE */
C52_STATION_FIRST_VEHICLE_LOG <- false;
/* P3 / A7.5 : une nouvelle ville ou industrie rend le portefeuille obsolete.
 * Le rafraichissement reactif est rare et evite d'attendre le prochain mois. */
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
HARD_ITERATION_CAP <- 5000;
/* V100 : memoire d'echec des doublements de voie (defaut 0). */
/* Garde geometrique rail : preserve l'identite [lead, station_exit], refuse avant depense les
 * raccords terminaux que le constructeur ne sait pas fermer, et ne memorise que les TRKFAIL
 * geometriques explicitement prouves persistants. Defaut 0 pendant qualification. */
RAIL_GEOMETRY_GUARD <- false;
/* Sous-interrupteurs diagnostiques du garde. Ils valent 1 pour reproduire exactement le
 * comportement candidat actuel lorsque rail_geometry_guard=1 ; ils sont sans effet si le garde
 * principal vaut 0. */
RAIL_GEOMETRY_EXACT_IDENTITY <- true;
RAIL_GEOMETRY_PREFILTER <- true;
RAIL_GEOMETRY_PAIR_MEMORY <- true;
/* V153 : raccordement terminal rail quand le dernier segment est un saut (pont/tunnel).
 * Defaut 0 pendant qualification. */
/* V156 : Revalidation incrementale du vivier indexee (0 historique, 1 indexee, 2 controle). */
const INCR_REVALIDATE_INDEX = 1;
/* Sondes de tentatives / refus de proximite ferroviaires, OFF par defaut. */
RAIL_FAILURE_AUDIT <- false;
/* Si un devis vivant STNFAIL sur le quai exact choisi avant l'A*, recalculer une fois les plans
 * de quai a longueur identique et ne garder qu'un plan exposant le meme [lead, station_exit].
 * Aucun nouvel A* ; defaut 0 pendant qualification. */
RAIL_GEOMETRY_LIVE_REPLAN <- false;
/* Optimisation experimentale des regenerations ciblees industrie : dans le fallback multi-cargo,
 * ignorer un cargo seulement si le catalogue prouve que l'industrie cible n'est ni source d'une
 * paire valide ni puits d'une paire valide pour CE cargo. Defaut 0 pendant qualification. */

/* C67.4 : carte par blocs dans le reliquat de tick, sans consommateur (contrat C67 §14).
 * 0 = service absent (défaut), 1 = service construit et rempli en fond. */
C67_TERRAIN_MAP <- false;

/* C67.6 : sonde passive d'exposition eau (task_terrain.nut), 0 = absente (défaut).
 * C67_SLACK_HOOK vaut vrai si au moins un service C67 utilise le reliquat de tick. */
C67_WATER_EXPOSURE <- false;
C67_SLACK_HOOK <- false;
C67_WATER_EXPO <- null;

/* C80 tranche 4 : sous C76, une couche industries ou moteurs non aeriens ne regenere que les
 * modes qui en dependent (rail, route, eau) au lieu du vivier entier. 0 = desactive (defaut). */

C80_MARGINAL_FLOOR_LEDGER <- null;

/* Sonde incrementale air sous probe_portfolio */
C80_AIR_INC_COUNTS <- { full = 0, targeted = 0, none = 0 };

/* C78 etape 2 : annee de la derniere generation aerienne journalisee par la sonde C78 etape 2. */
C78_GEN_LOG_YEAR <- -1;

/* V86 Variante B : plafond abaisse de routes par aeroport hub.
 * 0 = plafonds actuels (4 petits/commuter, 12 grands), 1..12 = min(plafond actuel, N). */
AIR_HUB_MAX_ROUTES <- 3;

/* V89 : débit de recherche A* rail opportuniste.
 * Avance des tranches supplémentaires tant qu'il reste du budget d'opcodes dans le tick,
 * sans bloquer la file de fond ni changer l'ordre des tâches. 0 = désactivé (défaut). */

/* V90 : A* ferroviaire rapide vendorisé (tracé identique, −8 % d opcodes par itération mesuré).
 * 0 = RailPathFinder BaNaNaS, 1 = OpexRailPathFinderV90 (défaut, décision utilisateur du 2026-09-24). */

/* V91 : heuristique pondérée A* rail (weighted A*).
 * Multiplicateur en pourcentage de l'estimation heuristique retournée par _Estimate.
 * 100 = non pondéré (V90 strictement inchangé), > 100 accélère la recherche au prix de tracés légèrement
 * sub-optimaux. Défaut 120 depuis le 2026-09-24 (décision utilisateur) : recherches ÷ 5, 20x10 neutre. */
V91_ASTAR_WEIGHT_PCT <- 120;

/* V129 : A* rail à exploration strictement identique mais moins coûteux en opcodes
 * (pathfinder_v90/v129.nut). 0 = code V90 inchangé (défaut). Sans effet si V90_FAST_PATHFINDER = 0. */

/* V131 : reparation locale d'un trace rail stocke/prepare (A* de contournement,
 * deplacement de quai, garde doublon). Defaut 0 : comportement et cout nuls. */
V131_RAIL_REPAIR <- false;
V131_REPAIR_MAX_TILES <- 35;
V131_REPAIR_MAX_RUNS <- 3;
V131_REPAIR_MAX_ITERS <- 2500;

/* V131 : degagement urbain (clearance) de l'A* rail pour eviter les centres-villes
 * et leurs emprises aeroportuaires futures. Defaut 0 : cout nul. */
V131_TOWN_CLEARANCE <- false;
V131_TOWN_CLEAR_BUFFER <- 4;

/* F-EVENT-BACKLOG-01 : ne relancer la reselection dans _c77RemoveSubsidy que si
 * la purge a reellement retire des candidats de subvention. 0 = inconditionnel (historique) ; defaut 1 depuis le 11/10. */

V147_IN_PHASE <- false;
V147_TASK_BASE <- -1;

/* V154 : insertion par dichotomie dans OpexProjectInsertDefensive (optimisation opcodes).
 * 0 = insertion lineaire historique (defaut) ; 1 = dichotomie sur cles mises en cache. */
SELECT_BISECT_STAMP <- 0;
V233_PENDING_CONTINUE <- false;
V233_GOODS_GRAFT <- false;
const V233_PLAN_LIMIT = 4;
const V233_PLAN_TTL_DAYS = 90;

const V233_GOODS_MIN_MONTHLY = 64;

/* V279 : re-selection incrementale exacte (0=historique, 1=memoise, 2=controle). */
V279_RESELECT_MEMO <- 0;
OPEX_LINES_REVISION <- 0;
OPEX_AIR_SITE_EPOCH <- 0;
OPEX_ABANDON_REVISION <- 0;
OPEX_AIR_ROLLBACK_REVISION <- 0;
V279_FILTER_STAMP_ID <- 0;
V279_LAST_MONTH <- -1;
V279_LAST_LINES_REV <- -1;
V279_LAST_SITE_EPOCH <- -1;
V279_LAST_ABND_REV <- -1;
V279_LAST_ROLLBACK_REV <- -1;
V279_LAST_HAS_LINES <- null;
V279_HITS <- 0;
V279_MISSES <- 0;
V279_LAST_STATS_MONTH <- -1;
