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
/* air_presite : sonder les deux sites en AITestMode avant d'engager le capital du premier
 * aeroport. Inerte par defaut jusqu'au verdict du banc. */
AIR_PRESITE <- false;
/* C33.2 : Arrets de rabattement joints dans le chantier aeroport */
AIR_JOINED_STOPS <- false;
/* Refaire le sac a dos contre la caisse vivante, sans repayer la generation des candidats. */
PORTFOLIO_FRESH_BUDGET <- false;
/* C36.1 : Caching incremental du vivier post-chantier. */
PORTFOLIO_CACHE <- false;
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
/* C32 : rabattement arbitre au portefeuille (1) au lieu de la tache dediee (0). */
FEEDER_PORTFOLIO <- true;
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

/* Reserve de tresorerie dynamique : adaptee a la taille de la flotte pour liberer le capital
 * des les premieres annees (15 000 £ au lieu de 50 000 £) et eviter les soldes oisifs. */
DYNAMIC_CASH_RESERVE <- true;
/* Decision utilisateur : la reserve ne doit jamais depasser UN mois d'entretien (totalRunning / 12),
 * contre jusqu'a 3 mois (quarterlyBuffer) ou un forfait fixe selon la branche. Defaut a false pour
 * ne rien changer tant que le banc n'a pas tranche -- voir OpexCashReserve() plus bas. */
RESERVE_MAINT_CAP <- false;
/* Marges de tresorerie exigees EN PLUS de la reserve, sur le chemin aerien. Decision utilisateur
 * du 2026-09-03, tirée du diagnostic 1v1 (docs/diag_1v1_decisions.json) : la marge de 30 000 £ est
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
TREE_PLANTING <- false;
PAX_FULL_LOAD <- true;
AIR_FULL_LOAD <- false;
COMPLEX_CARGO <- true;
AIR_STARTER <- true;
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
/* A7.5 : Invalidation reactif catalogue via ET_INDUSTRY_OPEN et ET_TOWN_FOUNDED */
EVENT_CATALOG_INVALIDATE <- false;
const CASH_RESERVE_STATIC = 25000;
const CASH_RESERVE_MIN = 5000;
const CASH_RESERVE_MAX = 25000;

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
  if (quarterlyBuffer < CASH_RESERVE_MIN) reserve = CASH_RESERVE_MIN;
  else if (quarterlyBuffer > CASH_RESERVE_MAX) reserve = CASH_RESERVE_MAX;
  else reserve = quarterlyBuffer;
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
/* Gain absolu minimal avant de rejouer la generation : en dessous, le cout en opcodes ne vaut pas
 * la peine d'etre paye pour quelques milliers de livres. */
const PORTFOLIO_REFRESH_MIN_GAIN = 50000;
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
 * trois defauts mesures tombent ensemble --
 *   1. rail_refleet redevient ATTEIGNABLE. Son bloc vit a l'interieur de _expandRailLines, derriere
 *      un return anticipe commande par rail_expand (defaut 0), et _runNextTask desactivait la tache
 *      sur le meme critere. Avec les defauts livres, aucune ligne rail ne pouvait donc jamais
 *      gagner un second train ni une seconde voie, alors qu'info.nut annonce rail_refleet actif.
 *   2. une ligne routiere neuve n'achete plus une seconde flotte complete dans son propre cycle de
 *      construction : `vehCount` n'etant ecrit qu'une fois par an, elle arrivait au refleet avec
 *      have = 0 et se faisait reconstruire, ordres dupliques compris.
 *   3. `isAnyWaiting` ne prend plus un vehicule en chargement pour un embouteillage. Sous
 *      OF_FULL_LOAD_ANY c'est l'etat normal d'un camion, et les trois heuristiques de croissance
 *      exigeant !isAnyWaiting, le signal etait inverse par rapport a son intention. */
FLEET_FIX <- false;

/* La croissance urbaine cede le pas au portefeuille (docs/taches.md S0 septies et S0 decies) :
 * repli FAUX jusqu'a la lecture unique de growth_yields dans Start(). Defaut 0 : chemin
 * historique inchange -- _tryTownGrowth depense des qu'il a de quoi payer, sur des candidats a
 * profit predit NUL. Sous 1, il exige en plus un surplus couvrant le capital que le portefeuille
 * s'est deja engage a depenser.
 *
 * MESURE le 2026-09-02 (docs/bench_growth_yields_3y.json, 20 graines x 3 ans, apparie) : REJETE.
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
 * ADOPTE le 2026-09-02, defaut 1 (docs/bench_air_margin_3y.json, 20 graines x 3 ans, apparie) :
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
 * ADOPTE le 2026-09-02, defaut 1 (docs/bench_air_abandon_3y.json, 20 graines x 3 ans, apparie) :
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
 * docs/diag_airfleet_monthly_5s3y.json) : la premiere ligne aerienne ouverte capte la tresorerie
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
  /* Transaction asynchrone d'expansion rail : le train roule vers son depot pendant que la
   * boucle principale continue par pas de dix jours. Jamais de Sleep bloquant dans la tache. */
  _railExpansion = null;
  /* Recherche A* ferroviaire reprise d'un tour de file a l'autre (docs/taches.md A4). Meme
   * patron que _railExpansion : l'etat vit ici, il est repris en TETE de _runNextTask, et on
   * termine en remettant _railSearch = null. Le pathfinder lui-meme est dans state.pathfinder. */
  _railSearch = null;
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
  _lastAirFleetMonth = -1;
  _lastRepayMonth = -1;
  /* G2 : une ouverture d'industrie ou fondation de ville rend le catalogue ET le
   * portefeuille derive perimes. dueCycle = 0 ne suffit pas : catalog peut deja
   * avoir tourne ce mois-ci et sortir par son garde de cadence. */
  _portfolioInvalidated = false;
  _startYear = -1;
  _vehiclesToScrap = null;
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
    this._abandonedPairs = {};
    this._abandonCounts = {};
    this._vehiclesToScrap = {};
    OpexAirResetSiteCache();
    this._activeSubsidies = {};
    this._subsidyStats = { offers = 0, expiredWithoutAward = 0, awardedSelf = 0, awardedOther = 0, matchedPool = 0 };
    /* Priorite : donnees et stop-loss, croissance des flottes existantes avant nouveaux projets,
     * portefeuille multimodal ROI, croissance urbaine, dette. */
    this._taskQueue = [
      { name = "catalog", dueCycle = 0, enabled = true },
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
  function _tryTownGrowth(year);
  function _runNextTask();
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
  local maxPerYear = AIR_STARTER ? 30 : 5;
  local maxTotal = AIR_STARTER ? 250 : 25;
  local margin = AIR_STARTER ? 2000 : AIR_CAPITAL_MARGIN;

  local maxBatch = AIR_STARTER ? 12 : 3;
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
     * 2026-09-02 (docs/bench_lotE_air_marge_3y.json) : -11,5 % de valeur (t = -2,66), -9,8 % de
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

    if (TREE_PLANTING) {
      OpexBoostTownRating(plan.siteA.town.id, 700, 35);
      OpexBoostTownRating(plan.siteB.town.id, 700, 35);
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
      if (AIR_ABANDON && ABANDON_MEMORY) {
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

    if (TREE_PLANTING) {
      OpexBoostTownRating(townId, 100, 15);
    }

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
    if (TREE_PLANTING) {
      if (candidate.srcTown >= 0) OpexBoostTownRating(candidate.srcTown, 700, 35);
      if (candidate.dstTown >= 0) OpexBoostTownRating(candidate.dstTown, 700, 35);
    }
    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    if (!result.ok) {
      if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
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
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_hard", extra = "" });
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
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
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
      if (!lowCash && TREE_PLANTING && candidate.kind == "pax") {
        OpexBoostTownRating(candidate.src, 700, 35);
        OpexBoostTownRating(candidate.dst, 700, 35);
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
      local maxPerYear = AIR_STARTER ? 30 : 5;
      local maxTotal = AIR_STARTER ? 250 : 25;
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

      if (TREE_PLANTING) {
        OpexBoostTownRating(plan.siteA.town.id, 700, 35);
        OpexBoostTownRating(plan.siteB.town.id, 700, 35);
      }

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
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=air src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
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


function OpexAI::_tryBuildProjects(year)
{
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
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  local builtCount = 0;
  local passDiscards = [];
  /* 1 conserve le break historique. Au-dela, chaque candidat apres le premier succes passe les
   * revalidations de son mode contre this._lines, la carte et la tresorerie vivantes. */
  local maxBatch = PORTFOLIO_MAX_BATCH;

  /* A4 : un A* termine au tour precedent a depose un railPlan sur le candidat stocke. On le
   * consomme AVANT le balayage du portefeuille, qui a pu etre regenere entre-temps. */
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase == "build") {
    local outcome = this._consumeRailSearch(year);
    if (outcome != "cash") {
      this._railSearch = null;
      if (outcome == "built") builtCount++;
    }
  }

  if (builtCount < maxBatch && this._projects != null && this._projects.best.len() > 0) {
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

    local mode = project.mode;
    local modeChar = mode == "rail" ? "T" : (mode == "road" ? "R" : (mode == "air" ? "A" : "W"));

    if (mode == "fleet") {
      local attempt = this._tryBuildFleetProject(year, project, i, passDiscards);
      passDiscards = attempt.discards;
      if (attempt.outcome == "built") {
        builtCount++;
        if (builtCount >= maxBatch) break;
      }
      continue;
    }

    if (mode == "air") {
      local attempt = this._tryBuildAirProject(year, project, i, builtCount, passDiscards,
                                                anchor, yy);
      passDiscards = attempt.discards;
      if (attempt.outcome == "built") {
        builtCount++;
        if (builtCount >= maxBatch) break;
      }
    } else if (mode == "road") {
      if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = project.src, dst = project.dst, reason = "road_disabled", extra = "" });
        continue;
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
          continue;
        }
        if (OpexTownRoadLineCount(this._lines, candidate.src) >= 4) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          continue;
        }
        if (!isFeeder && OpexTownRoadLineCount(this._lines, candidate.dst) >= 4) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          continue;
        }
      } else {
        if (OpexOriginServed(this._lines, candidate.src, true)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "src_origin_served", extra = "" });
          continue;
        }
        if (OpexOriginServed(this._lines, candidate.dst, true)) {
          if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "dst_origin_served", extra = "" });
          continue;
        }
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        continue;
      }

      local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        continue;
      }

      OpexSign(anchor, "IP|" + yy + "|R|" + project.budgetScore + "|" + project.opcodeScore);

      this._budget.begin();
      local planning = OpexRoadPlanFor(this._catalog, candidate);
      local planOps = this._budget.end("build_road_plans");
      local plan = planning.plan;
      local idx = this._nextLineId;
      if (plan == null) {
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=plan_failed detail=" + planning.reason);
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
        OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|0");
        continue;
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
        continue;
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
      if (TREE_PLANTING) {
        if (candidate.srcTown >= 0) OpexBoostTownRating(candidate.srcTown, 700, 35);
        if (candidate.dstTown >= 0) OpexBoostTownRating(candidate.dstTown, 700, 35);
      }
      local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
      OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|" + result.opcodes);
      if (!result.ok) {
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
        continue;
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
      builtCount++;
      if (builtCount >= maxBatch) break;
    } else if (mode == "rail") {
      local attempt = this._tryBuildRailProject(year, project, i, builtCount, passDiscards,
                                                 anchor, yy);
      passDiscards = attempt.discards;
      if (attempt.outcome == "pending") {
        /* En batch historique > 1, le portefeuille doit etre regenere avant de reprendre un
         * A* suspendu. Le defaut unitaire conserve le retour immediat d'origine. */
        if (builtCount > 0) break;
        return true;
      }
      if (attempt.outcome == "built") {
        builtCount++;
        if (builtCount >= maxBatch) break;
      }
    } else if (mode == "water") {
      local attempt = this._tryBuildWaterProject(year, project, i, builtCount, passDiscards,
                                                  anchor, yy);
      passDiscards = attempt.discards;
      if (attempt.outcome == "built") {
        builtCount++;
        if (builtCount >= maxBatch) break;
      }
    }
  }
  if (DECISION_LOG && builtCount == 0 && logDiscardsThisPass && passDiscards.len() > 0) {
    local maxLog = passDiscards.len() < 3 ? passDiscards.len() : 3;
    for (local k = 0; k < maxLog; k++) {
      local d = passDiscards[k];
      OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
    }
  }
  }

  /* G4§1 : l'ancien chemin deduisait hadAbandons de passDiscards, dont le remplissage
   * est garde par DECISION_LOG (defaut 0). Le drapeau _hadAbandonsThisPass est pose
   * directement par _markPairAbandoned, couvrant tous les chemins (air, route, rail
   * bloquant et reprenable via _consumeRailSearch). */
  local hadAbandons = this._hadAbandonsThisPass;

  if (builtCount > 0 || hadAbandons) {
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (PORTFOLIO_CACHE && this._projects != null && (("budgetCandidates" in this._projects) || ("candidateGroups" in this._projects))) {
      local budgetNow = OpexAvailableCapital();

      this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs);
    } else {
      local priorPeak = (this._projects != null && ("capitalBudgetPeak" in this._projects))
          ? this._projects.capitalBudgetPeak : 0;
      local priorHistory = (this._projects != null && ("capitalBudgetHistory" in this._projects))
          ? this._projects.capitalBudgetHistory : null;
      this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines, priorPeak, priorHistory, fleetPlan, this._abandonedPairs);
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
             + this._projects.stats.selectedCapital + "|B" + builtCount);
    /* L'abandon a maintenant ete consomme par la reelection/reconstruction. */
    if (hadAbandons) this._hadAbandonsThisPass = false;
    return true;
  }
  return false;
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
     * sur 3 parties x 2 ans (docs/diag_1v1_decisions.json). */
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
  if (!slice.done) return;

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
    if (money < need) return "cash";
  }

  if (TREE_PLANTING && candidate.kind == "pax") {
    OpexBoostTownRating(candidate.src, 700, 35);
    OpexBoostTownRating(candidate.dst, 700, 35);
  }
  local result = OpexBuildLine(this._catalog, this._budget, candidate, state.alternativeRatio,
                               join, OpexCashReserve(), state.hardCap);
  /* Ne pas jeter le plan sur CASH : on reessaiera au prochain tour, sans refaire l'A*. */
  if (result.reason == "CASH") return "cash";
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
  }
}

/* File CONTINUE : le scan reprend apres la derniere tache choisie, meme si un A* a franchi le
 * changement d'annee. Le calendrier ne decide plus RIEN : quand le suffixe de la table est fini,
 * _taskCycle avance et le scan repart a zero. Chaque tache se reporte par dueCycle, donc aucun
 * item ne peut affamer ceux places apres lui et le dernier rend litteralement la main au premier. */
function OpexAI::_runNextTask()
{
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
  if (this._railSearch != null) this._continueRailSearch();
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
      if (budgetNow > budgetThen + PORTFOLIO_REFRESH_MIN_GAIN &&
          budgetNow > budgetThen * 2) stale = true;
    }
    /* Une invalidation evenementielle prime toujours la cadence mensuelle et le seuil de
     * tresorerie : le portefeuille est derive du catalogue, pas seulement du capital. */
    if (this._lastCatalogMonth == ym && this._projects != null && !stale &&
        !this._portfolioInvalidated) return false;
    this._lastCatalogMonth = ym;
    this._pruneAbandonedPairs(date);
    this._catalog.refresh(this._budget, year);
    local priorPeak = (this._projects != null && ("capitalBudgetPeak" in this._projects))
        ? this._projects.capitalBudgetPeak : 0;
    local priorHistory = (this._projects != null && ("capitalBudgetHistory" in this._projects))
        ? this._projects.capitalBudgetHistory : null;
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines, priorPeak, priorHistory, fleetPlan, this._abandonedPairs);
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
    this._tryTownGrowth(year);
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
  local roadPaxCatchment = AIController.GetSetting("road_pax_catchment_pct");
  if (roadPaxCatchment > 0) ROAD_PAX_CATCHMENT_SHARE_PCT = roadPaxCatchment;
  local roadStopHouses = AIController.GetSetting("road_stop_catchment_houses");
  if (roadStopHouses > 0) ROAD_STOP_CATCHMENT_HOUSES = roadStopHouses;
  local roadPaxDwell = AIController.GetSetting("road_pax_dwell_days");
  if (roadPaxDwell >= 0) ROAD_PAX_STOP_DWELL_DAYS = roadPaxDwell;
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
  PORTFOLIO_FLOOR_PCT = AIController.GetSetting("portfolio_floor_pct");
  FLEET_FIX = AIController.GetSetting("fleet_fix") != 0;
  ECONOMY_FIX = AIController.GetSetting("economy_fix") != 0;
  GROWTH_YIELDS = AIController.GetSetting("growth_yields") != 0;
  AIR_MARGIN = AIController.GetSetting("air_margin") != 0;
  AIR_ABANDON = AIController.GetSetting("air_abandon") != 0;
  MIN_DISTANCE = AIController.GetSetting("rail_min_distance");
  PRICING_ROAD_RATING = AIController.GetSetting("pricing_road_rating") != 0;
  PRICING_RAIL_DEPOT = AIController.GetSetting("pricing_rail_depot") != 0;
  PRICING_ROAD_OPS = AIController.GetSetting("pricing_road_ops") != 0;
  RAIL_COST_PROBE = AIController.GetSetting("rail_cost_probe") != 0;
  AIR_COST_PROBE = AIController.GetSetting("air_cost_probe") != 0;
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
  AIR_HUB_FIX = AIController.GetSetting("air_hub_fix") != 0;
  TENSION_PROBE = AIController.GetSetting("tension_probe") != 0;
  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
    OpexTensionEnable(this._budget);
  }
  AIR_DEMAND_CAP = AIController.GetSetting("air_demand_cap") != 0;
  AIR_DEMAND_PLAN = AIController.GetSetting("air_demand_plan") != 0;
  DYNAMIC_PATHFINDER_CAP = AIController.GetSetting("dynamic_pathfinder_cap") != 0;
  TREE_PLANTING = AIController.GetSetting("tree_planting") != 0;
  PAX_FULL_LOAD = AIController.GetSetting("pax_full_load") != 0;
  AIR_FULL_LOAD = AIController.GetSetting("air_full_load") != 0;
  COMPLEX_CARGO = AIController.GetSetting("complex_cargo") != 0;
  AIR_STARTER = AIController.GetSetting("air_starter") != 0;
  AIR_HUB = AIController.GetSetting("air_hub") != 0;
  local airMaxDist = AIController.GetSetting("air_max_distance");
  if (airMaxDist >= 0) AIR_MAX_DISTANCE = airMaxDist;
  local afcd = AIController.GetSetting("air_fleet_cadence_days");
  if (afcd >= 0) AIR_FLEET_CADENCE_DAYS = afcd;
  local afb = AIController.GetSetting("air_fleet_buffer");
  if (afb >= -1) AIR_FLEET_BUFFER = afb;
  local rtf = AIController.GetSetting("rail_terrain_factor");
  if (rtf > 0) RAIL_TERRAIN_FACTOR = rtf;
  RAIL_REFLEET = AIController.GetSetting("rail_refleet") != 0;
  FEEDER_ENABLED = AIController.GetSetting("feeder_enabled") != 0;
  EVENT_DEPOT_SELL = AIController.GetSetting("event_depot_sell") != 0;
  EVENT_INDUSTRY_CLOSE = AIController.GetSetting("event_industry_close") != 0;
  EVENT_SUBSIDY_PROBE = AIController.GetSetting("event_subsidy_probe") != 0;
  EVENT_VEHICLE_LOST = AIController.GetSetting("event_vehicle_lost") != 0;
  EVENT_CATALOG_INVALIDATE = AIController.GetSetting("event_catalog_invalidate") != 0;
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
  this._startYear = AIDate.GetYear(AIDate.GetCurrentDate());
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=initial_borrow amount=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount());
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
        if (!this._runNextTask()) break;
        drained++;
      }
      /* Le plancher garde de la marge pour ne pas etre suspendu au milieu d'une transaction, et
       * le plafond de taches empeche un tour de file entierement compose de taches inutiles de
       * bruler le budget en pur ordonnancement. */
      if (drained == 0) this._runNextTask();
      /* AUCUN Sleep ici, et c'est deliberé. Le Sleep de fin de tour rendait la main alors qu'il
       * restait du budget, ce qui est un auto-handicap face a une IA qui ne dort pas entre ses
       * chunks (docs/philosophie_armes_egales : les bridages servent aux parties avec des HUMAINS,
       * jamais entre IA). Le moteur nous suspend de lui-meme quand le budget du tick est epuise et
       * nous reprend au tick suivant exactement ou il nous avait laisses : la boucle reste donc
       * bornee, et la partie avance normalement. */
    } else {
      this._runNextTask();
      AIController.Sleep(1);
    }
  }
}
