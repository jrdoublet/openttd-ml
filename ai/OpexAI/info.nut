class OpexAI extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA qui traite les opcodes comme une ressource de jeu : chaque candidat porte un profit attendu ET un cout en opcodes attendu, et le budget va au meilleur rapport."; }
  function GetVersion()     { return 4; }
  function GetDate()        { return "2026-08-29"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }

  /* Les reglages debug_signs et pathfinder_sleep_ticks existent pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains (loan_repay_floor_k, pathfinder_hard_cap_k,
   * abandon_memory, station_join, join_max_distance, origin_sitable, basin_share, reborrow, road_mode, road_refleet, road_multistop, astar_cost, probe_negative et pax_near, eux, sont des parametres de conception exposes au banc,
   * pas des bridages).
   * Entre IA, la regle est l'inverse : jouer a armes egales,
   * donc ne jamais s'auto-handicaper face a un adversaire qui ne se bride pas. Un handicap non intentionnel
   * invalide silencieusement le banc (sweeps/bench.py contre AAAHogEx) : l'ecart mesure ne
   * viendrait plus des decisions de l'IA. D'ou les defauts choisis ci-dessous. */
  function GetSettings()
  {
    /* Panneaux de diagnostic. Defaut ACTIF, et ce n'est pas negociable a la legere : les
     * ~38 appels AISign.BuildSign de main.nut sont la SEULE source de mesure de tous les harnais
     * sweeps/*.py (AILog.Info n'apparait pas dans la sortie capturee par OpenTTDLab, verifie le
     * 2026-08-28). Passer ce reglage a 0 par defaut casserait silencieusement toute
     * l'instrumentation du projet. On le met a 0 pour une partie avec des humains, ou les
     * panneaux saturent la carte sans leur apporter quoi que ce soit. */
    AddSetting({
      name = "debug_signs",
      description = "Diagnostic signs on the map: 1 = current behaviour (required by sweeps/), 0 = none (use when playing with humans)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Plancher de tresorerie sous lequel on ne rembourse pas l'emprunt, EN MILLIERS.
     *
     * DEFAUT 300 (= 300 000) DEPUIS LE 2026-08-29, apres mesure au banc apparie -- voir le verdict
     * en fin de commentaire. Il valait 1000 avant, et c'est ce que reproche la mesure ci-dessous.
     *
     * CE QUE LA MESURE DU 2026-08-29 REPROCHE A CETTE VALEUR (docs/opexai_emprunt.json, 6 graines
     * x 20 ans, panneaux LB/LF) : la tresorerie d'OpexAI reste entre 50 000 et 400 000 pendant
     * DIX A QUATORZE ANS. Le plancher est donc hors d'atteinte pendant toute la phase de
     * croissance, et l'emprunt initial de 300 000 court a 5 % sans qu'aucun remboursement ne
     * puisse seulement etre tente. La regle elle-meme est saine : des que la tresorerie franchit
     * le million, le remboursement part immediatement et solde tout. C'est le seuil qui est faux,
     * pas le mecanisme -- et une hypothese concurrente a ete REFUTEE au passage : l'appel place
     * apres _tryBuild ne bloque rien (0 annee sur les 6 graines ou le sommet annuel passait le
     * plancher mais pas le creux).
     *
     * POURQUOI 300 SERAIT LE BON ORDRE DE GRANDEUR, sur deux mesures independantes : le plus gros
     * candidat jamais bloque faute de tresorerie coute 248 106 (mediane 136 760), et la
     * construction d'une annee draine 95 172 en mediane, 183 101 au 90e centile. Un plancher de
     * 300 000 couvre donc la plus grosse ligne observee, et le controle ayant lieu APRES
     * _tryBuild, la construction de l'annee est de toute facon deja payee quand il s'applique.
     * La courbe est plate entre 300 et 500 (meme annee de deblocage sur 4 graines sur 6), et
     * descendre a 200 passerait sous le cout de la plus grosse ligne : 300 est le genou.
     *
     * /!\ LE REEMPRUNT N'EST PLUS ABSENT, il est derriere le reglage `reborrow` (defaut 0).
     * Sans lui, rembourser ici reste a sens unique : une compagnie desendettee qui rencontre
     * un candidat plus cher que sa tresorerie renonce a la ligne. Le plancher 300 couvre la
     * plus grosse ligne observee (248 106) donc le trou est borne tant que reborrow reste a 0.
     *
     * VERDICT DU BANC APPARIE (docs/bench_v2_emprunt.json, 20 graines x 20 ans, OpexAI contre
     * OpexAI[loan_repay_floor_k=300]) : adopte.
     *   - Metrique directe, la seule decisive ici : graines a emprunt residuel 3/20 -> 1/20, et
     *     emprunt total residuel 900 000 -> 230 000. Les graines 100 et 4096 passent de 300 000 a
     *     zero, et leur NOTE bondit (170 -> 245 et 269 -> 309) alors que leur valeur d'entreprise
     *     ne bouge quasiment pas -- exactement le comportement attendu, puisque rembourser avec du
     *     cash est neutre en valeur et ne gagne que l'interet plus la composante "emprunt a zero".
     *   - Aucun dommage global : company_value appariee t = -0,12 (-0,17 %), performance_history
     *     t = +1,18 (+1,91 %). Les deux sont sous le plancher de detection du banc (~15 % et ~12 %,
     *     cf. docs/taches.md S5) : c'etait PREVU, et c'est pourquoi la lecture se fait sur
     *     current_loan et non sur la valeur.
     *   - Preuve que le changement est chirurgical : sur 4 graines (17, 999, 2026, 8675309) les
     *     deux bras sont BIT A BIT identiques -- la ou la tresorerie franchissait le million d'un
     *     coup, abaisser le plancher ne change litteralement rien.
     *   - Reste 1 graine (42) a 230 000 SUR CE BANC. Sur l'arbre courant elle solde tout en 1975
     *     (docs/opex_reborrow_20y_42.json). Descendre le plancher sous 300 passerait sous le
     *     cout de la plus grosse ligne ; `reborrow` (ci-dessous) ne paie pas : le trou
     *     "desendetter puis manquer d'argent" est vide. */
    AddSetting({
      name = "loan_repay_floor_k",
      description = "Cash floor below which the loan is not repaid, in thousands: 300 = measured default, 1000 = pre-2026-08-29 behaviour",
      min_value = 0, max_value = 2000,
      easy_value = 300, medium_value = 300, hard_value = 300,
      custom_value = 300,
      step_size = 50,
      flags = 0
    });

    /* Reemprunt a la demande. Defaut 0 DEPUIS LE 2026-08-29, apres mesure : le trou est vide.
     *
     * CE QUE 1 FAIT. Quand un candidat (rail, route, air, eau) depasse cash + CASH_RESERVE,
     * on tire le palier d'emprunt manquant -- arrondi vers le haut a GetLoanInterval(), bride
     * a GetMaxLoanAmount() -- jamais le maximum d'un coup. Le chemin ou la tresorerie suffisait
     * deja ne paie aucun appel d'emprunt. Panneau GL|year|drew|newLoan|ok sur un tirage reel.
     *
     * POURQUOI CE N'EST PAS "remettre l'emprunt au max chaque annee". L'emprunt a zero vaut 5 %
     * de la note de compagnie, et un emprunt qui dort coute 4 % : emprunter plus que le candidat
     * en cours paierait de l'interet pour de l'argent qui ne construit pas. Le remboursement
     * annuel (_tryRepayLoan) et ce tirage sont le meme levier, dans les deux sens.
     *
     * VERDICT (5 graines x 20 ans, docs/opex_reborrow_20y_42.json et
     * docs/opex_reborrow_20y_4seeds.json) : 412 GC, 0 tirage, 0 GC avec de l'emprunt encore
     * disponible. Tous les blocages cash sont des annees ou l'emprunt est DEJA au plafond
     * (300 000). Des que le remboursement commence, plus aucun GC. Le mur n'est pas l'absence
     * de reemprunt, c'est le plafond d'emprunt lui-meme -- deja nomme au mur n deg 1. Un banc
     * apparie n=20 mesurerait le bruit d'un mecanisme inerte : on ne le lance pas.
     * OpexAI[reborrow=1] rallume. Le code reste : le trou se rouvrirait si le plancher
     * descendait sous le prix d'une ligne. */
    AddSetting({
      name = "reborrow",
      description = "Borrow the missing loan step when a candidate exceeds cash: 1 = enabled, 0 = historical one-way repay (unmeasured default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Table de cout A*. Defaut 0 DEPUIS LE 2026-08-30, apres banc apparie.
     *
     * CE QUE 1 FAIT. OpexRailIterations lit KNOT_ITERATIONS_V2 : iterations
     * amorties par succes, fenetre +/-12 tuiles, 227 tentatives sous 15.3
     * (docs/opex_attempt_distance_20y_5seeds.json). ATTEMPT_MULTIPLIER reste 4 :
     * p95(iter OK)/amort <= 2,7. Le plancher 2000 absorbe le court.
     *
     * 5 graines (docs/opex_astar_cost1_20y_5seeds.json) : on construit encore
     * (13-20 lignes), mediane 51->47 tuiles, tentatives et ABND baissent.
     * Le piege "budgets 50-400, zero ligne" est evite.
     *
     * VERDICT n=20 (docs/bench_astar_cost.json) : company_value -8,9 %, t = -1,86,
     * 7/20 -- sous le plancher ~15 %. performance_history -5,3 %, t = -1,81.
     * Gares -7,9 %, t = -3,23, 4/20 : CA c'est etabli. MIN_RATIO coupe le long
     * sans le remplacer 1:1 par du court. Defaut 0. OpexAI[astar_cost=1] rallume. */
    AddSetting({
      name = "astar_cost",
      description = "A* cost knots: 0 = OpenTTD 13.4 TrainLineAI table (control), 1 = amortized iterations per success under 15.3 (227 attempts)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Sondage des paires rejetees pour profit predit <= 0. Defaut 0 : MESURE, pas un classement.
     *
     * CE QUE 1 FAIT. OpexMakeCandidate range les PROBE_STASH_K=12 paires les moins negatives
     * (plus proches de 0) sans les livrer au TOP_K. Apres _tryBuild, au plus UNE de ces
     * paires est force-construite, si tropClose et le capital le laissent. Le budget est
     * HARD_ITERATION_CAP (alternativeRatio 0, chemin Z) : le premier sondage a 2 000
     * itérations (MIN_RATIO -> plancher) a abandonne 48/52 tentatives, mediane 123 tuiles.
     * PX marque la ligne pour qu'elle ne contamine pas la calibration des lignes classees.
     *
     * POURQUOI CE N'EST PAS UN CHANGEMENT DE POLITIQUE. Le filtre profit<=0 n'a ete
     * calibre que sur les paires qui passent. Le premier sondage a montre que le pax
     * 60-75 tuiles rejete rapporte 10-20 k/an (n=4) ; le long, qui est le volume, etait
     * censure par le plancher. 0 reproduit le classement historique EXACT ; 1 est le
     * bras de mesure. Ne PAS retuner OpexLineEconomics ni MIN_RATIO dans le meme pas.
     * OpexAI[probe_negative=1] rallume. */
    AddSetting({
      name = "probe_negative",
      description = "Force-build one leftover-cash rail pair rejected for predicted profit <= 0, once per year: 1 = measure selection bias, 0 = historical ranking (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Retuning pax borne. Defaut 0 : attendre le banc apparie.
     *
     * CE QUE 1 FAIT. Les paires pax, distance <= 100, profit predit dans (-200, 0]
     * entrent au classement (ratio = 1, sous MIN_RATIO). _tryBuild en tente au plus
     * une par an au plafond dur. Fret et pax >100 restent rejetes a profit<=0.
     *
     * POURQUOI CES BORNES. Sondage a 40 000 iterations (docs/opex_probe_negative_hardcap_20y_5seeds.json) :
     * 11/11 pax <=100 rentables en derniere annee (predit -146..-9, reel 10-20 k) ;
     * >100 tuiles, mediane reelle 0. Lever le filtre partout readmettrait le long
     * du vivier. -200 couvre l'echantillon sans ouvrir le gouffre.
     *
     * VERDICT n=20 (docs/bench_pax_near.json) : company_value +0,6 %, t = 0,10,
     * 8/20 -- nul. performance_history +4,7 %, t = 1,42, 14/20 -- sous le
     * plancher ~12 %. Gares +10,5 %, t = 4,27, 17/20 : CA c'est etabli, on
     * construit plus pour la meme valeur. C'est le vivier. Defaut 0.
     * OpexAI[pax_near=1] rallume. */
    AddSetting({
      name = "pax_near",
      description = "Admit passenger rail pairs of at most 100 tiles with predicted profit in (-200, 0] into ranking: 1 = enabled, 0 = historical profit<=0 rejection (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Plafond absolu du pathfinder, EN MILLIERS d'iterations. La campagne 2026-08-29 (4 graines
     * x 20 ans) a mesure 52 reussites et 5 ABND : les abandons a 60 000 absorbaient 56,5 % des
     * opcodes de construction. La plus longue reussite etait a 36 600 iterations ; 40 000 lui
     * laisse 9 % de marge tout en coupant les recherches qui avaient deja depasse leur cout
     * d'opportunite. Le reglage conserve 60 comme bras de controle lisible au banc. */
    AddSetting({
      name = "pathfinder_hard_cap_k",
      description = "Hard pathfinder iteration cap, in thousands: 40 = measured default, 60 = pre-2026-08-29 behaviour",
      min_value = 5, max_value = 100,
      easy_value = 40, medium_value = 40, hard_value = 40,
      custom_value = 40,
      step_size = 5,
      flags = 0
    });

    /* Un ABND est seulement l'epuisement du budget d'iterations, pas une ligne construite puis
     * defectueuse. La meme paire peut sinon revenir au classement l'annee suivante et repayer le
     * plafond : 4096 l'a fait trois fois dans la mesure du 2026-08-29. La memoire est une petite
     * table de l'instance, indexee par paire stable, pas une liste balayee. */
    AddSetting({
      name = "abandon_memory",
      description = "Remember rail origin/destination/cargo pairs after ABND: 1 = enabled, 0 = pre-2026-08-29 behaviour",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Le filet MIN_SEPARATION reste la protection de bassin : 1 ne l'abaisse pas, il remplace
     * seulement le rejet d'UNE extremite par un quai rail dedie joint a la gare existante. Depuis
     * le 2026-08-29 (seconde tranche), ce reglage commande AUSSI la relaxation d'origine a la
     * generation : a 0, une paire dont une seule extremite est servie est ecartee comme avant,
     * donc 0 reste le comportement historique EXACT et le bras de controle du banc apparie.
     *
     * DEFAUT 0 DEPUIS LE 2026-08-29, CONFIRME APRES TRACTION. Le mecanisme marche : le vivier ne
     * s'eteint plus, les jointures ont lieu. Deux bancs apparies, 20 graines x 20 ans :
     *   - avant traction (docs/bench_v2_vivier.json) : vehicules +37,2 %, t = 5,94, 18/20 ;
     *     company_value -0,3 %, t = -0,03 ;
     *   - apres traction (docs/bench_join_after_traction.json) : vehicules +23,6 %, t = 3,50,
     *     17/20 ; gares -11,9 %, t = -3,61 (reemploi du StationID) ; company_value +5,9 %,
     *     t = 0,96, 11/20 -- sous le plancher ~15 %. Sans la graine 1337 (+132 %) il reste
     *     +1,6 %, t = 0,34. On construit plus, sur moins de gares, pour la meme valeur.
     *
     * CE QUI N'EST PAS LA CAUSE. Le double comptage de monthly a une origine servie a ete mesure
     * (docs/opex_join_bias.json) et, une fois type, distance et epoque neutralises, son intervalle
     * contient 1. Corriger monthly sur ce chiffre brut serait le piege deja desamorce.
     *
     * SUITE : basin_share a ete mesure, defaut 0, et ne paie pas (les jointures sont
     * declassees, l'IA repose des gares neuves). Le spread n'est PAS la suite : il
     * convertirait des NOPLAN en jointures sur un classement qui ne paie pas.
     * docs/aaahogex_rail_join.md reste la note d'idees, pas un plan.
     *
     * REFUS (2026-08-30). OB|R decompose le null : 196 M, 75 K, 0 R, 41 other, 705
     * tentatives, 39 OK, 0 JOINPATH (docs/opex_join_refuse_20y_5seeds.json). R meurt
     * a la generation. JOINPATH est vide. Les echecs sont SITEA/SITEB.
     *
     * RENDEMENT (2026-08-30). OpexJoinPlatformPlans cherche offset 1-4, pas le spread.
     * 39 -> 71 OK (5,5 % -> 15,7 %), SITE 692 -> 393, 361 nClear=0 restants au quai
     * joint (docs/opex_join_parallel_20y_5seeds.json). 5/5 plus de vehicules, 4/5
     * moins de valeur. Le spread n'est pas la suite.
     *
     * H1 (2026-08-30). Population encore longue (docs/opex_join_pop.json).
     * join_max_distance=50 : 29 OK, dist 37, D=1035. Coupe le vivier, ne bat
     * pas join=0. Defaut 0. H2 ensuite. */
    AddSetting({
      name = "station_join",
      description = "Reuse one compatible nearby OpexAI rail station with a dedicated platform: 1 = enabled, 0 = historical too-close rejection",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Porte H1 sur la jointure. Defaut 0 : pas de plafond, la v1 inchangee.
     * N > 0 : si OpexFindStationJoin a reussi mais candidate.distance >= N,
     * rejet tooClose historique, zero A*. Inerte si station_join = 0.
     * Valeur de travail 50 (docs/opex_join_pop.json) : jointures <50 tuiles
     * reel/pred 1,12, 2 trains ; >=100 : 0,07 et 4 trains. Ne pas baisser
     * MIN_RATIO global. OpexAI[station_join=1,join_max_distance=50]. */
    AddSetting({
      name = "join_max_distance",
      description = "Reject a station join when the pair is this long or longer (tiles); 0 = no cap (v1)",
      min_value = 0, max_value = 200,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 5,
      flags = 0
    });

    /* Filtre d'origine rail constructible. Defaut 0 DEPUIS LE 2026-08-29, apres banc apparie.
     *
     * CE QUE 1 FAIT. Avant le classement, une source fret dont le bassin n'a aucune tuile de
     * TERRE voyant le cargo (eau, ou le batiment d'industrie lui-meme) n'entre pas au TOP_K.
     * Mesure graine 42 / 20 ans : 23 NOPLAN / 46 tentatives -> 0, les 14 M d'opcodes par SITEA
     * disparaissent. Le puits n'est PAS filtre : le couper enlevait des paires urbaines encore
     * constructibles.
     *
     * VERDICT DU BANC APPARIE (docs/bench_noplan_sitable.json contre docs/bench_traction_new.json,
     * 20 graines x 20 ans) : pas d'effet etabli. company_value +4,0 % (t = 0,50, 11/20),
     * performance_history +1,9 % (t = 0,85), vehicules -1,1 %. Sous le plancher de detection.
     * Le minimum recule (1,79 M -> 1,18 M) et le CV passe de 0,28 a 0,34. La graine 42 seule
     * recule de 28 %. 0 reste le bras historique EXACT du classement ; 1 pour rejouer le
     * mecanisme sans relire le code. */
    AddSetting({
      name = "origin_sitable",
      description = "Drop rail candidates whose source has no land tile seeing the cargo: 1 = enabled, 0 = historical ranking (measured default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Partage de bassin sur une gare jointe. Defaut 0 DEPUIS LE 2026-08-29, apres banc apparie.
     *
     * CE QUE 1 FAIT. Quand une extremite du candidat reutilise un StationID deja a nous, la
     * production de CETTE extremite est divisee par (lignes rail deja sur ce StationID pour ce
     * cargo + 1). Le dest fret n'est PAS divise. Inerte si station_join = 0.
     *
     * VERDICT (docs/bench_basin_share.json, paire docs/bench_basin_share_paired.json, 20 graines
     * x 20 ans, les deux bras a station_join=1) : pas d'effet etabli en valeur.
     * company_value +5,5 % (t = 0,89, 11/20), performance_history +3,8 % (t = 1,11), sous le
     * plancher. Les vehicules ne bougent pas (+0,2 %, t = 0,04). Les gares REBONDISSENT
     * (+12,9 %, t = 3,67, 15/20) : le partage declasse les jointures, l'IA repose des gares
     * neuves. Ce n'est pas "moins de trains sur un bassin partage", c'est un autre classement.
     * Graine 42 : tentatives de jointure 228 -> 40, mais vehicules 221 -> 238. 0 reste le bras
     * join du banc post-traction. */
    AddSetting({
      name = "basin_share",
      description = "Split a joined station's production across rail lines on that StationID: 1 = enabled, 0 = count the catchment as if the station were new (measured default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Mode route. Defaut 1 depuis le 2026-08-29, et c'est un changement de politique, pas un
     * reglage de confort.
     *
     * CE QUE LA MESURE QUI L'AVAIT DESACTIVE DISAIT VRAIMENT. La v1 batissait une seule liaison
     * bus et rendait -599/an pendant 19 ans sur la graine gelee. Mais les deux notes d'arret y
     * etaient a -1 tout du long : le bus n'a jamais charge un seul passager. Le chiffre condamnait
     * donc un BUG -- le bit de route perpendiculaire absent des facades, cf. builder_road.nut --
     * et non la rentabilite d'une desserte routiere. Ce bug est corrige, et la comparaison
     * "9 lignes rail contre 16" qui accompagnait ce verdict etait de toute facon non attribuable :
     * une seule graine, un ecart bien sous le plancher de detection du banc (~15 % sur
     * company_value, docs/taches.md S5).
     *
     * CE QUE LE MODE FAIT MAINTENANT, ET POURQUOI C'EST UN AUTRE PARI. Ce n'est plus une liaison
     * passagers unique mais une phase annuelle qui bâtit jusqu'a ROAD_MAX_NEW_LINES_PER_YEAR
     * petites lignes, dont -- c'est l'essentiel -- des lignes de FRET par camion, industrie vers
     * industrie et industrie vers ville. Le pari tient en une phrase : sur 5 a 25 tuiles, un
     * camion n'a ni voie, ni signaux, ni gare, donc son capital est d'un ordre de grandeur sous
     * celui du rail, et la bande de distance ou le rail perd de l'argent (MIN_DISTANCE = 25, une
     * mesure) peut lui etre rentable. Le wiki previent qu'une courte liaison BUS "ne sera
     * probablement pas tres rentable" (docs/mecanique_jeu.md S11) -- il ne dit rien de tel du
     * fret, et notre plancher ROAD_MIN_PROFIT_ANNUAL laisse justement passer le second en coupant
     * le premier quand il est marginal.
     *
     * VERDICT DU BANC APPARIE (docs/bench_v2_road.json, 20 graines x 20 ans, OpexAI contre
     * OpexAI[road_mode=0]) : ADOPTE, sur la metrique que le projet a designee comme la bonne entre
     * variantes d'OpexAI.
     *   - performance_history : +36,6 points appariés (+9,3 %), t = 2,03, la route gagne sur
     *     16 graines sur 20. Test des signes bilateral : p = 0,012. C'est la lecture decisive --
     *     performance_history est moins bruitee que company_value chez nous (CV 31 % contre 45 %
     *     sur ce banc), cf. docs/taches.md S5.
     *   - company_value : +232 433 (+9,6 %) mais t = 1,50 et 13 graines sur 20 seulement. NON
     *     concluant, et entierement otage d'une seule graine -- voir ci-dessous.
     *
     * 🔴 LE PRIX A CONNAITRE ETAIT une graine sur vingt (8675309) a 1, sur le banc d'adoption
     * (docs/bench_v2_road.json, pre-traction). SUR L'ARBRE COURANT ce n'est plus vrai
     * (docs/bench_road_8675309.json) : 2 368 267 contre 2 282 217 a road_mode=0, emprunt 0,
     * months_of_bankruptcy 0. Les deux bras sont identiques au 1er janvier 1971. Campagne
     * 20 ans : 0 tentative routiere -- le continue-not-break de la traction laisse le rail
     * prendre le cash residual, le break cash de la route ne s'exerce plus. Pas de garde-fou
     * a ecrire. Le +9,3 % d'adoption n'a PAS ete rejoue apres traction.
     *
     * SITEA/B (2026-08-30). OpexRoadSites saute les tuiles non constructibles : 48 sondes
     * etaient brulees sur des maisons/industries qui ont du cargo. 5 graines : SITE
     * 14/18 -> 0, OK 2 -> 6 (docs/opex_road_sitable_20y_5seeds.json).
     *
     * TRACEX (2026-08-30). 32 L (contre 12) et facade vers l'autre bout. nLong=0.
     * 5 graines : TRACEX 5->2, OK 6->8, pax 2->4 (docs/opex_road_tracex_20y_5seeds.json). */
    AddSetting({
      name = "road_mode",
      description = "Build short road lines (bus town-town, and truck freight industry-industry / industry-town): 1 = enabled, 0 = rail-only baseline",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Reconstitution de flotte routiere. Defaut 1 : c'est un correctif, pas un pari.
     *
     * CE QUE 1 FAIT. Apres _reportLines / _scrapDeadLines, une ligne routiere dont vehCount
     * est sous predTrains (borne a MAX_ROAD_VEHICLES = 2), dont le depot et les arrets
     * tiennent encore, et qui n'est pas en rebut, recoit les vehicules manquants. S'il en
     * reste un, clone + ordres partages ; s'il n'en reste aucun, moteur du catalogue +
     * ordres reconstitues. Avant _tryBuild : l'infrastructure est deja payee.
     *
     * POURQUOI CE N'EST PAS DU RENOUVELLEMENT AUTOMATIQUE. SetAutoRenew remplace un vehicule
     * qui approche de l'age maximal. Il ne remplace pas un vehicule DETRUIT (passage a
     * niveau : un train est le seul objet qui detruise un vehicule routier) ni un
     * renouvellement refuse faute de cash au moment T. Une ligne a zero vehicule n'a plus
     * rien a renouveler.
     *
     * MESURE DU TROU, plusieurs campagnes graine 42 : opex_road_20y_42 ligne pax 15
     * (2 en 1985, 1 en 1986, 0 en 1987-89, 9000/an puis notes 54 -> -1) ;
     * opex_join_20y_42 COAL 2->1->0 pour 8 ans vides.
     * VERDICT (docs/opex_refleet_20y_4seeds.json, graine 42, 20 ans) : COAL 15 passe 2->1
     * en 1982 et 1988 ; RF ajoute 1 chaque fois, rating 22->61 puis 29->67, jamais a zero.
     * Defaut 1. OpexAI[road_refleet=0] rallume l'abandon silencieux. */
    AddSetting({
      name = "road_refleet",
      description = "Rebuild a road line's fleet when vehicles drop below the original count: 1 = enabled (bugfix default), 0 = leave empty infrastructure idle",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Multistop routier. Defaut 0 : un arret par bout, flotte bornee a 2.
     *
     * CE QUE 1 FAIT. Apres les deux arrets primaires, tente un arret extra a chaque
     * extremite, meme facade, tuile cardinale voisine, joint par l'identifiant du
     * primaire (pas STATION_JOIN_ADJACENT : piege de deux gares voisines). Un echec
     * d'extra n'annule pas la ligne. Des vehicules au-dela de candidate.trains seulement
     * si les DEUX bouts ont double (2 berths x min(nA,nB)), cash au-dessus de
     * CASH_RESERVE. Le classement et MAX_ROAD_VEHICLES restent a 2.
     *
     * POURQUOI DEFAUT 0. Le wiki promet x5 de volume ; ce n'est pas mesure. Extra
     * stop + clones coutent du cash hors modele. OpexAI[road_multistop=1] allume. */
    AddSetting({
      name = "road_multistop",
      description = "Join a second road stop at each end and add vehicles only if both ends doubled: 1 = try, 0 = one stop per end (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Ticks de sommeil apres chaque bloc de PATH_CHUNK (50) iterations d'A*.
     *
     * Defaut 0 = AUCUN bridage. Choisi PAR PRINCIPE (armes egales entre IA), PAS par la mesure --
     * voir la reserve en fin de commentaire. On croyait AAAHogEx dormir toutes les
     * 50 iterations ; c'est l'inverse, verifie dans son source le 2026-08-28 :
     *   - ai/AAAHogEx-115/pathfinder.nut:202-216 (rail) : boucle _FindPath(50) sans AUCUN Sleep ;
     *   - ai/AAAHogEx-115/road.nut:914-919 (route) : FindPath(100) puis HogeAI.DoInterval(), qui
     *     retourne immediatement si la date n'a pas avance (main.nut:3865-3875) -- le seul
     *     Sleep(10) est dans la branche force, jamais empruntee la.
     * Le chunk de 50 est bien commun aux deux, mais le Sleep etait propre a OpexAI
     * (builder_rail.nut::OpexSearchPath) : ~3 a 7 % de la duree de recherche perdus, toujours en
     * notre defaveur face a lui.
     *
     * /!\ CE QUE LA MESURE NE DIT PAS. Sur la campagne gelee graine 42/20 ans, sleep=0 a donne
     * 13 lignes / 2 336 785 contre 13 lignes / 2 756 947 a sleep=1. On NE peut PAS en conclure que
     * le Sleep aide : le controle a sleep=1 n'a lui-meme pas reproduit la baseline d'avant ce
     * commit (16 lignes / 2 787 970) -- le seul fait d'interposer OpexSign devant les 57 panneaux,
     * sans changer aucune decision, a suffi a faire perdre 3 lignes. Toute perturbation du rythme
     * d'opcodes deplace les frontieres de ticks et fait diverger la trajectoire. Avec une erreur-
     * type de 11,8 % a 5 graines (docs/taches.md S5), une graine unique ne peut pas trancher un
     * ecart de cet ordre.
     *
     * DECISION ARRETEE LE 2026-08-29, NE PAS ROUVRIR. Le defaut reste 0 et ne sera PAS mesure au
     * banc multi-graines, alors meme que le banc existe desormais (sweeps/bench_v2.py sait opposer
     * OpexAI a OpexAI[pathfinder_sleep_ticks=1]). Raison : le Sleep est strictement domine, il n'y
     * a aucun mecanisme par lequel il puisse aider. Le moteur suspend deja le script des qu'il
     * epuise son budget d'opcodes du tick, donc Sleep(n) n'achete aucun opcode supplementaire plus
     * tard -- il fait seulement qu'OpexAI ne fait rien pendant n ticks pendant qu'un adversaire
     * continue. Le 13-contre-13 de la graine 42 etait du bruit de trajectoire, pas un signal.
     * Depenser 25 minutes de banc a le confirmer serait payer pour une conclusion connue.
     * Mettre 1 (ou plus) pour rendre la main plus souvent dans une partie avec des humains. */
    AddSetting({
      name = "pathfinder_sleep_ticks",
      description = "Ticks slept after each 50-iteration A* chunk: 0 = no self-handicap (equal terms vs other AIs), 1+ = yield more often (use when playing with humans)",
      min_value = 0, max_value = 10,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });
  }
}

RegisterAI(OpexAI());
