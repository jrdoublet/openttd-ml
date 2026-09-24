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
/* Taille du batch du portefeuille. Repli 1 jusqu'a la lecture unique de
 * portfolio_max_batch dans Start() : 1 garde le break apres le premier succes, donc le chemin
 * livre reste strictement le meme. */
PORTFOLIO_MAX_BATCH <- 1;
/* C38 : le batch dynamique re-classe le vivier apres chaque succes contre la caisse vivante.
 * Il reste desactive jusqu'au diagnostic puis au banc apparie ; a 0 le chemin livre ne porte
 * aucun etat de batch supplementaire. */
/* P2 : le bras C38 ne doit pas balayer tout le vivier sur une rafale de refus,
 * ni consommer tout le tick. Ces controles ne sont lus que pour le bras
 * dynamique ; 0 reconstitue respectivement l'ancien balayage et son garde
 * absolu de 2 500 opcodes. */
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
/* Marge d'autorite aerienne appliquee PAR PLAN dans OpexAirEconomics (builder_air.nut) plutot
 * qu'en rabotant maxCapital chez l'appelant. Voir le commentaire de la boucle de dimensionnement
 * (builder_air.nut) pour le raisonnement complet et le banc a -11,5 % qu'il corrige.
 *
 * ADOPTE le 2026-09-02, defaut 1 (results/bench_air_margin_3y.json, 20 graines x 3 ans, apparie) :
 * company_value +1,3 % (t = 0,26), profit_year -1,6 % (t = -0,28), toutes metriques sous t = 1,2.
 * NEUTRE, donc adopte pour la JUSTESSE, pas pour la performance -- ne revendiquer aucun gain. Le
 * defaut vise est reel mais son cout est nul : le gachis
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
OPEX_AIR_SITE_PAD <- false;
OPEX_AIR_TOWN_PAD <- false;
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
 * inchange. Sous les switches restants, deux incoherences de modele tombent, toutes dans l'arbitrage MULTIMODAL --
 * c'est-a-dire la ou le portefeuille compare rail et route sur des nombres qui n'etaient pas
 * calcules de la meme facon :
 * L'estimation d'opcodes d'un projet routier utilise le tarif du pathfinder routier. */
PRICING_ROAD_OPS <- true;
/* air_roi_order (2026-09-03) : ordre de service de la croissance de flotte aerienne.
 * _resizeAirFleets parcourait _lines dans l'ordre de CONSTRUCTION -- ce n'etait pas une decision
 * de conception, juste l'ordre du tableau. Consequence mesuree (5 graines x 3 ans,
 * results/diag_airfleet_monthly_5s3y.json) : la premiere ligne aerienne ouverte capte la tresorerie
 * a chaque passage, et les autres ne grandissent JAMAIS -- 0 croissance sur 3 graines / 5, et
 * +1 avion par an au mieux ailleurs. Aucun effet compose n'apparait nulle part.
 * 1 (defaut) sert d'abord la ligne au meilleur profit PAR APPAREIL, donc celle qui rembourse
 * l'avion suivant le plus vite ; 0 rend l'ordre historique pour que le banc puisse trancher. */
AIR_ROI_ORDER <- true;
/* Retuning pax borne : repli FAUX jusqu'a la lecture unique de pax_near dans Start().
 * Defaut 0. 1 admet au classement les pax <=100 tuiles a predit > -200, une
 * tentative/an au plafond dur. Le long et le fret restent filtres. */
PAX_NEAR <- false;
/* Croissance urbaine : repli VRAI jusqu'a la lecture unique de town_growth dans Start().
 * Complete avec 5-n stations de bus pour chaque ville desservie comptant n gares/aeroports. */
TOWN_GROWTH_ENABLED <- true;
TOWN_GROWTH_SKIP_NOOP <- false;
/* Memoire des echecs de planification town_growth : une ville n'est replanifiee que si son nombre
 * de maisons a change depuis l'echec (mesure : 20 villes replanifiees jusqu'a 41 fois en 6 ans pour
 * TRACEX/DEPOTX, 97 % d'echecs). */
TOWN_GROWTH_PLAN_MEMO <- false;
/* C87 : ligne de croissance urbaine construite seulement si son profit annuel predit est positif,
 * et fermee apres deux annees pleines deficitaires. La ville refusee est memorisee dans
 * _abandonedPairs (cle "town_growth|<townId>", sauvegardee et purgee au meme delai).
 * Defaut 1 depuis le 2026-09-24 par decision utilisateur (les bus deficitaires pesent sur la note). */
TOWN_GROWTH_ROI_GATE <- true;
