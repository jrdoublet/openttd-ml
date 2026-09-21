/* C65 passe 2 : globales du bloc APRES require(builder_road.nut),
 * donc apres TOP_K de candidates.nut. */
/* Le classement ne contient que TOP_K = 20 candidats. Le plafond de continuation est exactement
 * cette borne existante, pas un second seuil arbitraire : une annee sans argent examine au plus
 * 20 candidats, donc au plus 20 appels de solde et de _tooClose, sans lancer A* avant le test de
 * cash. L'ancien break en examinait 1 ; parcourir les 19 restants est le cout borne qui rend enfin
 * visible un candidat moins rentable par iteration mais financable en capital. */
TOP_K <- 20;
CASH_CANDIDATE_SCAN_LIMIT <- TOP_K;
/* Compatibilite historique uniquement : ces deux constantes ne sont plus lues par la phase
 * routiere actuelle. Elles NE constituent donc pas des plafonds actifs et ne doivent pas etre
 * citees comme tels dans un banc. Conservees pour ne pas casser un ancien script/require qui
 * referencerait encore leur symbole. */
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
_lastProjectScanMonth <- -1;
/* La memoire est l'autre correctif, independamment des 40 000 iterations. Elle reste un repli
 * actif jusqu'a la lecture unique de abandon_memory dans Start(), comme les autres reglages de
 * decision qui ne changent pas pendant une partie. */
ABANDON_MEMORY <- true;
/* C33.3 : Cooldown en jours avant réessai d'une paire abandonnée (defaut 365, adopte ; 0 = permanent). */
ABANDON_COOLDOWN_DAYS <- 0;
/* C22 : Filtrer les paires abandonnées dès la génération des candidats (defaut 1, adopte). */
ABANDON_GEN_FILTER <- false;
/* H1 : constante historique conservee bit-identique. */
JOIN_MAX_DISTANCE <- 0;
/* Filtre d'origine sitable : repli ACTIF jusqu'a la lecture unique de origin_sitable dans
 * Start(). Defaut passe a 1 le 2026-09-09 (decision utilisateur) ; 1 ecarte du TOP_K les
 * sources sans tuile de terre voyant le cargo dans leur bassin. Le classement a 0 reste celui
 * d'avant le filtre, conserve pour l'A/B. */
ORIGIN_SITABLE <- true;
/* Partage de bassin : repli FAUX jusqu'a la lecture unique de basin_share dans Start().
 * Defaut 0 apres banc apparie. */
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
/* Taille du batch du portefeuille. Repli 1 jusqu'a la lecture unique de
 * portfolio_max_batch dans Start() : 1 garde le break apres le premier succes, donc le chemin
 * livre reste strictement le meme. */
PORTFOLIO_MAX_BATCH <- 1;
/* C38 : le batch dynamique re-classe le vivier apres chaque succes contre la caisse vivante.
 * Il reste desactive jusqu'au diagnostic puis au banc apparie ; a 0 le chemin livre ne porte
 * aucun etat de batch supplementaire. */
PORTFOLIO_DYNAMIC_BATCH <- false;
/* P2 : le bras C38 ne doit pas balayer tout le vivier sur une rafale de refus,
 * ni consommer tout le tick. Ces controles ne sont lus que pour le bras
 * dynamique ; 0 reconstitue respectivement l'ancien balayage et son garde
 * absolu de 2 500 opcodes. */
DYNAMIC_BATCH_REJECT_LIMIT <- 3;
DYNAMIC_BATCH_OPS_BUDGET_PCT <- 50;
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
/* Plancher de profit absolu du portefeuille v2, en POURCENTAGE du meilleur profit finançable du
 * moment. Repli 0 (= tri au seul ratio) jusqu'a la lecture de portfolio_floor_pct dans Start().
 * Voir projects.nut::OpexProjectSelectAffordable pour le mecanisme et la mesure qui l'impose. */
PORTFOLIO_FLOOR_PCT <- 0;
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
/* C56 follow-up: an airport failure belongs to a physical anchor, not only to
 * the pair which happened to propose it. Experimental until its paired bench. */
AIR_ABANDON_SITE <- false;
/* C63/C58 : memoire experimentale d'une ville qui refuse un nouvel aeroport parce que sa
 * limite de stations est atteinte. Defaut 0 jusqu'au banc causal C66.4. */
AIR_TOWN_LIMIT_MEMORY <- false;
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
 *   2. l'estimation d'opcodes d'un projet routier ne facture plus ses iterations au tarif du
 *      pathfinder RAIL -- une erreur de dimension qui sous-estimait opcodeScore cote route. */
PRICING_ROAD_RATING <- false;
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
