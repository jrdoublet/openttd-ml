class OpexAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA multimodale : meilleur ROI par origine/destination, puis revenu maximise sous contraintes de capital et d'opcodes."; }
  function GetVersion()     { return 6; }
  function GetDate()        { return "2026-09-01"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "13"; }

  /* Les reglages debug_signs et pathfinder_sleep_ticks existent pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains (loan_repay_floor_k, pathfinder_hard_cap_k,
   * abandon_memory, station_join, join_max_distance, join_place, origin_sitable, basin_share, reborrow, road_mode, road_pax_catchment_pct, road_refleet, road_multistop, marginal_fleet, astar_cost, probe_negative et pax_near, eux, sont des parametres de conception exposes au banc,
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
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });


    AddSetting({
      name = "rail_cost_probe",
      description = "Emit per-line rail model capital versus actual construction cost: 1 = measurement only, 0 = no extra signs (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Symetrique aerien de rail_cost_probe, et il manquait la ou l'argent part le plus :
     * l'attribution du 2026-09-02 met 64,5 % du capital sur l'avion, mais ce chiffre est le
     * MODELE (panneau AH|), le seul disponible. AC| donne le cout REEL, nivellement compris, et
     * il est emis aussi sur ECHEC -- c'est le seul moyen de chiffrer un aeroport bati puis rase
     * (4 BFAIL sur 20 tentatives au banc, docs/taches.md S0 unvicies). */
    AddSetting({
      name = "air_cost_probe",
      description = "Emit per-attempt air model capital versus actual cost, including levelling and rolled-back airports: 1 = measurement only, 0 = no extra signs (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Le catalogue mensuel fige le capital AVANT les taches air et air_fleet. Sur la graine 42,
     * 295 000 GBP a la generation devenaient 24 013 GBP au passage projects : le sac a dos
     * optimisait donc un budget qui n'existait plus. Ce bras ne rejoue que la selection bon marche
     * sur le vivier deja genere ; defaut 0 jusqu'au banc apparie. */
    AddSetting({
      name = "portfolio_fresh_budget",
      description = "Reselect the generated project portfolio against current cash immediately before building: 1 = enabled, 0 = monthly frozen budget (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Sonde les DEUX sites en AITestMode avant de batir le premier aeroport. L'ordre historique
     * batit A, decouvre B impossible, puis demolit A : 4 BFAIL sur 20 tentatives, tous en
     * premiere annee, quand la tresorerie est au plus juste.
     *
     * Le sondage vient APRES le nivellement des deux sites, et c'est essentiel : les 8 echecs
     * mesures sont 7 x ERR_FLAT_LAND_REQUIRED et 1 x ERR_AREA_NOT_CLEAR, jamais un refus
     * municipal -- sonder le terrain brut rejetterait precisement les sites que LevelTiles
     * repare. Le nivellement des deux sites est deja paye dans le chemin nominal.
     *
     * Defaut 0 jusqu'au banc apparie : economiser un aeroport rase est un gain evident sur le
     * papier, mais c'est exactement ce que disaient les treize corrections de S0 nonies bis. */
    /* _resizeAirFleets n'emet que ses SUCCES (panneau FG|). Quand une ligne aerienne cesse de
     * grandir -- et la mesure du 2026-09-02 dit 2,2 avions par ligne pour un plafond de 16 --
     * la cause est invisible. FR| donne le PREMIER refus rencontre, une fois par ligne et par an. */
    /* La note de gare est un MULTIPLICATEUR, pas un bonus : 51 % de la note vient du delai depuis
     * le dernier ramassage (docs/mecanique_jeu.md S3). Une ligne mal servie effondre sa note et
     * degrade tout ce qu'elle touche -- donc on regle l'existant avant d'ajouter une liaison.
     *
     * Ce n'est pas un arbitrage mais un ORDRE DE SERVICE, et la mesure dit pourquoi : la
     * croissance de flotte aerienne est refusee 31 fois sur 32 pour TRESORERIE, jamais pour le
     * plafond de l'aeroport (1,6 avion par ligne pour un plafond de 16, docs/taches.md
     * S0 quinvicies). Quand `air` passe en premier, il ne reste rien pour `air_fleet`.
     *
     * ⚠️ Defaut REMIS A 0 le 2026-09-02 : deux bancs apparies 20 graines concordent contre.
     * A 3 ans, profit annuel -20,4 % (t = -3,53) ; a 10 ans, valeur -18,3 % (t = -3,81, 5 graines
     * gagnantes sur 20, p = 0,041) et profit annuel -11,5 % (t = -2,70, p = 0,003). L'hypothese
     * "3 ans est la phase de ruee, ça paiera a 10" est REFUTEE : c'est pire a 10 ans.
     * Lecture : pour l'aerien, la LARGEUR bat la PROFONDEUR. Une liaison neuve ouvre un flux
     * entier, un appareil de plus n'ajoute qu'une tranche marginale d'une ligne existante. Le
     * raisonnement sur la note de gare reste juste ; il est simplement domine. */
    AddSetting({
      name = "fleet_before_new",
      description = "Serve air fleet growth before building new air lines: 1 = tune what exists first, 0 = historical order (default, measured better)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_fleet_probe",
      description = "Emit the reason an air line's fleet did not grow, once per line per year: 1 = measurement only, 0 = no extra signs (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_presite",
      description = "Probe both airport sites in test mode before committing capital to the first one: 1 = enabled, 0 = build A then discover B (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_max_distance",
      description = "Plafond de distance pour les liaisons aeriennes (0 = illimite, 212 = defaut empirique, docs/taches.md C6)",
      min_value = 0, max_value = 1000,
      easy_value = 212, medium_value = 212, hard_value = 212,
      custom_value = 212,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "rail_terrain_factor",
      description = "Pourcentage applique au cout du rail par tuile (100 = brut, 170 = calibre sur le reel, docs/taches.md C2)",
      min_value = 50, max_value = 300,
      easy_value = 170, medium_value = 170, hard_value = 170,
      custom_value = 170,
      step_size = 5,
      flags = 0
    });

    AddSetting({
      name = "feeder_enabled",
      description = "Tache dediee de rabattage bus vers les hubs aeriens/ferroviaires (docs/taches.md C1): 1 = active (defaut), 0 = desactive",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "transit_cost",
      description = "Penalisation du capital immobilise en transit au denominateur du ROI (pour mille, docs/taches.md C9): 0 = neutre (defaut), 1000 = cout complet",
      min_value = 0, max_value = 2000,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 50,
      flags = 0
    });

    AddSetting({
      name = "rail_devis",
      description = "Devis reel par AITestMode + AIAccounting avant engagement ferroviaire (docs/taches.md C7): 1 = actif (defaut), 0 = desactive",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Expansion marginale d'une ligne rail existante. Le bras 1 ne cherche aucun nouveau
     * chemin : apres deux releves de saturation sur une ligne a une rame, il ajoute un wagon
     * dans la marge de quai deja payee, seulement si le revenu reel recale predit un gain net.
     * Defaut 0 jusqu'au banc apparie : le mecanisme et ses panneaux EG/EX restent alors absents
     * du chemin de controle. */
    AddSetting({
      name = "rail_expand",
      description = "Add one wagon to profitable saturated one-train rail lines using paid platform margin: 1 = enabled, 0 = control (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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
      description = "Hard pathfinder iteration cap, in thousands (docs/taches.md A3): 10 = A3 probe default, 40 = pre-A3 behaviour",
      min_value = 5, max_value = 100,
      easy_value = 10, medium_value = 10, hard_value = 10,
      custom_value = 10,
      step_size = 5,
      flags = 0
    });

    /* Recherche A* ferroviaire reprise d'un tour de file a l'autre (docs/taches.md A4,
     * S0 undecies ter). Mesure du 2026-09-03 : 7 mois consecutifs sans aucune action
     * (graine 100, juin-dec 1971) pendant un A* rail, parce que OpexSearchPath rebouclait
     * sur FindPath(50) sans jamais rendre la main a _runNextTask. Defaut 0 = comportement
     * actuel, pour que le banc puisse attribuer : ce changement modifie l'entrelacement
     * donc les decisions. */
    AddSetting({
      name = "rail_search_resumable",
      description = "Resume rail A* across task-queue turns so other tasks run during a long search (docs/taches.md A4): 1 = sliced, 0 = blocking (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Pathfinding segmente (docs/taches.md A5). Sonde 2026-09-03 : 40 % des tentatives
     * rail meurent en ABND. A3 a plafonne a 10k, donc l'objectif n'est plus d'accelerer
     * les succes mais de convertir les abandons. Port de TrainLineAI-segmented.
     * Banc 20 graines x 10 ans (docs/bench_rail_segmented_10y.json) : le mecanisme
     * marche (+13 % de gares, +5,5 % de vehicules) mais la valeur est NEUTRE
     * (-3,4 %, t = -0,86, 7/20, p = 0,26 -- non significatif).
     * Defaut 1 par decision de l'utilisateur du 2026-09-03 : on garde le reseau plus
     * dense et la recherche moins chere comme socle des mesures suivantes (A4 retest). */
    AddSetting({
      name = "rail_segmented_search",
      description = "Segmented rail pathfinding (docs/taches.md A5): 1 = segmented (default), 0 = classic A*",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Un ABND est seulement l'epuisement du budget d'iterations, pas une ligne construite puis
     * defectueuse. La meme paire peut sinon revenir au classement l'annee suivante et repayer le
     * plafond : 4096 l'a fait trois fois dans la mesure du 2026-08-29. La memoire est une petite
     * table de l'instance, indexee par paire stable, pas une liste balayee. */
    AddSetting({
      name = "abandon_memory",
      description = "Remember rail origin/destination/cargo pairs after ABND: 1 = enabled, 0 = pre-2026-08-29 behaviour",
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
     * pas join=0. Defaut 0. H2 (join_place) mesure, ne paie pas. */
    AddSetting({
      name = "station_join",
      description = "Reuse one compatible nearby OpexAI rail station with a dedicated platform: 1 = enabled, 0 = historical too-close rejection",
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

    /* H2 : joindre au lieu. Defaut 0 APRES MESURE 2026-08-30.
     * 1 = candidats depuis chaque gare rail OpexAI vers une origine
     * libre (bande 25-75, capee par join_max_distance si > 0), objet
     * join attache a la generation. Quai parallele 1-4, StationID du
     * primaire, JOINPATH dedie. PBS sur quais joints et aiguillage depot.
     * Independant de station_join (v1 = repli _tooClose).
     *
     * 5 graines (docs/opex_join_place_20y_5seeds.json) : 50 OK, dist 50,
     * reel/pred an 2 -0,16. Mediane company_value -64 % vs join=0
     * (5/5, graine 100 -92 %). TOP_K pollue, SITEA au quai joint.
     * Moins de vehicules ET moins de valeur. Pas de banc n=20.
     * OpexAI[join_place=1]. */
    AddSetting({
      name = "join_place",
      description = "Place-first rail join from an existing OpexAI station to a free origin (25-75 tiles): 1 = enabled, 0 = off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
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
     * CE QUE LE MODE FAIT MAINTENANT. Ce n'est plus une liaison passagers unique mais une famille
     * de projets, dont -- c'est l'essentiel -- des lignes de FRET par camion, industrie vers
     * industrie et industrie vers ville. Sur 5 a 25 tuiles, un camion n'a ni voie, ni signaux, ni
     * gare, donc son capital est souvent d'un ordre de grandeur sous celui du rail. Depuis la
     * chaine ROI, le rail couvre aussi cette bande : projects.nut compare les deux modes sur la
     * meme paire au lieu de donner la priorite a l'un d'eux. Le wiki previent qu'une courte
     * liaison BUS "ne sera probablement pas tres rentable" (docs/mecanique_jeu.md S11) -- le
     * modele economique tranche desormais chaque cas, sans plancher de profit eliminatoire avant
     * l'arbitrage modal.
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
     * a ecrire. Re-baseline 2026-08-30 : `docs/bench_road_current.json`, 20 graines × 20 ans,
`road_mode=1` contre `road_mode=0` avec traction et `road_pax_catchment_pct=86` :
performance_history +70,35 (+15,3 %), t = 5,65, 18/20 ; company_value +13,5 %, t = 2,24.
Le mode route est donc reconfirme sur l arbre courant.
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
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Croissance urbaine : cibler 5 gares/stations par ville desservie en ajoutant des stations de bus.
     * Defaut 1. S'il y a n gares ferroviaires/aeroports, complete avec 5-n stations de bus
     * intra-urbaines pour atteindre le plafond de croissance maximale du moteur OpenTTD (CountActiveStations=5). */
    AddSetting({
      name = "town_growth",
      description = "Boost served town growth with bus feeder stations (target 5 active stations per town): 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    
    /* Réserve de trésorerie dynamique adaptée aux coûts d'entretien réels (15 000 à 50 000 £).
     * Libère jusqu'à 35 000 £ au démarrage pour accélérer l'investissement initial. */
    AddSetting({
      name = "dynamic_cash_reserve",
      description = "Scale cash reserve with fleet maintenance (15k-50k) instead of static 50k: 1 = enabled (default), 0 = static 50k",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Plafond d'itérations A* dynamique : faible au départ (15k) pour filtrer vite les lignes faciles,
     * augmente en précalcul / attente de cash (60k) et avec la maturité du réseau (15k -> 60k). */
    AddSetting({
      name = "dynamic_pathfinder_cap",
      description = "Dynamically scale pathfinder opcode cap (15k early -> 60k low-cash/mature): 1 = enabled (default), 0 = static cap",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Ordre de chargement passagers rail : 1 = OF_FULL_LOAD_ANY (attente plein chargement aux deux bouts),
     * 0 = OF_NONE (chargement partiel et depart immediat pour maximiser la cadence et la note). */
    AddSetting({
      name = "pax_full_load",
      description = "Rail passenger load order: 1 = full load any (default), 0 = no full load (fast partial departure)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Gestion des marchandises complexes et chaines d'industries secondaires (Goods, Food, Mail, etc.) :
     * 1 = livre les marchandises transformees (usines/raffineries) aux villes acceptatrices (defaut),
     * 0 = fret primaire industrie-industrie uniquement (mode historique). */
    AddSetting({
      name = "complex_cargo",
      description = "Support complex secondary cargo chains and town goods/food deliveries: 1 = enabled (default), 0 = primary only",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Politique de capacite aerienne, sans priorite modale :
     * 1 = marge de depart reduite, plafond de lignes releve et expansion de flotte (defaut) ;
     * 0 = politique de capacite historique lente (1 ligne/an, max 5). */
    AddSetting({
      name = "air_starter",
      description = "Air capacity policy: 1 = aggressive fleet/line caps (default), 0 = historical slow capacity (1/yr, max 5)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Reutilisation d'un aeroport existant comme hub. Defaut 0 tant que le gain marginal
     * (un aeroport + un avion) n'a pas ete etabli au banc face aux paires disjointes. */
    AddSetting({
      name = "air_hub",
      description = "Reuse a profitable uncongested airport for a new destination: 1 = experimental hub routes (default), 0 = two new airports",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Expansion et doublement des lignes ferroviaires saturees (double voie et 2e train securise) :
     * 1 = double les lignes saturees avec 2e voie/depot et signaux PBS (defaut),
     * 0 = allongement de rame uniquement (mode historique). */
    AddSetting({
      name = "rail_refleet",
      description = "Double saturated rail lines with parallel track, PBS signals and 2nd train: 1 = enabled (default), 0 = consist elongation only",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Plantation d'arbres PREVENTIVE, avant toute tentative de construction (air, route, rail,
     * croissance urbaine) : 1 = plante systematiquement, 0 = off (defaut).
     *
     * ⚠️ Ce reglage ne commande QUE la plantation preventive, celle des sept sites gardes par
     * TREE_PLANTING dans main.nut. Le recours REACTIF reste actif en permanence et n'est pas
     * derriere ce drapeau : builder_air.nut appelle OpexBoostTownRating puis reessaie
     * l'aeroport uniquement quand BuildAirport a renvoye un vrai ERR_LOCAL_AUTHORITY_REFUSES.
     * C'est la regle voulue : on ne plante que si une ville nous refuse un aeroport.
     *
     * 0 est adopte apres le banc apparie 20 graines x 3 ans
     * (docs/bench_treeplanting_3y_20seeds.json) : couper la plantation preventive vaut
     * company_value +22,1 % (t = 2,42, 17/20 graines gagnantes), profit +26,8 % (t = 2,09),
     * profit_year +20,1 %, et resserre la dispersion (CV 63,8 % -> 50,7 %). L'effet depasse
     * le plancher de detection du banc (~15 % sur company_value). La depense d'arbres tombait
     * au moment ou le capital initial est le plus contraint. */
    AddSetting({
      name = "tree_planting",
      description = "Preventive tree planting before every build to raise town authority rating: 1 = enabled, 0 = off (default). The reactive retry after an airport refusal stays active regardless.",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Part de la production totale d une ville qu un arret de bus capte, en pourcentage.
     *
     * 86 est adopte apres le banc apparie 20 graines (docs/bench_road_pax_catchment.json) :
     * performance_history +22,2 points (+4,19 %), t = 2,48, 14/20 graines gagnantes ;
     * company_value -1,32 %, sans effet etabli. Le 0 reconstitue le calibrage rail historique
     * a 22 %. Ce reglage ne change que OpexRoadPaxCandidates, jamais le rail ni le fret. */
    AddSetting({
      name = "road_pax_catchment_pct",
      description = "Town production share captured by each bus stop, percent: 86 = measured route default; 0 = historical 22% rail-calibrated control",
      min_value = 0, max_value = 100,
      easy_value = 86, medium_value = 86, hard_value = 86,
      custom_value = 86,
      flags = 0
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
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Dimensionnement marginal et progressif de flotte. Defaut 0 : chemin actuel inchange (achat
     * immediat de tout ce que le modele predit, plafonds generiques MAX_ROAD_VEHICLES/16/4 avions
     * par an). Diagnostic banc apparie 20 graines contre AAAHogEx : ~85 % de l'ecart de profit vient
     * du volume (8x moins de vehicules/gares), le reste (~15 %) d'un rendement par vehicule
     * ajoute -31,4 %, avec 3,26 vehicules/gare contre 2,71 -- du capital immobilise plutot que
     * redeploye en nouvelles lignes. 1 fait demarrer chaque nouvelle ligne au minimum viable (1
     * vehicule/avion), et ne grandit qu'apres un profit REEL mesure, borne par une contrainte
     * physique/marginale (quais route reellement joints, age >= 1 an + charge complete en attente +
     * 1 avion/an en air) plutot que par une constante generique. Non mesure au banc, defaut choisi
     * par prudence -- OpexAI[marginal_fleet=1] pour l'evaluer. */
    AddSetting({
      name = "marginal_fleet",
      description = "Start new lines with the minimum viable fleet and grow only after measured profit, bounded by a physical/marginal cap: 1 = marginal sizing, 0 = buy the full model prediction upfront (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Ordre de service de la croissance de flotte aerienne (docs/taches.md S0 undecies ter).
     * L'ordre historique etait celui du tableau _lines, donc l'anciennete : la premiere ligne
     * ouverte captait la tresorerie a chaque passage et les autres ne grandissaient jamais
     * (0 croissance sur 3 graines / 5, +1 avion/an au mieux ailleurs). */
    AddSetting({
      name = "air_roi_order",
      description = "Serve air fleet growth best-yield-first (profit per aircraft) instead of oldest-line-first: 1 = yield order (default), 0 = historical build order",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Drainage du budget d'opcodes du tick. Revue du controleur, docs/taches.md S0 sexies point 1.
     *
     * 0 (defaut, comportement historique) : la boucle principale de Start() execute EXACTEMENT une
     * tache par tick puis Sleep(1). Le budget de 10 000 opcodes par tick n'etant PAS reportable,
     * un tick qui tire une tache hors de sa periode (catalog hors de son mois, report hors de son
     * annee, repay hors du sien) depense quelques centaines d'opcodes et JETTE les ~9 700 restants.
     * Sur une partie de 3 ans (~81 000 ticks, ~810 M d'opcodes) c'est le gisement dont AAAHogEx
     * tire ~150 gares quand nous en tirons ~18.
     *
     * 1 : on enchaine les taches tant que GetOpsTillSuspend() depasse LOOP_BUDGET_FLOOR, avec un
     * plafond LOOP_BUDGET_MAX_TASKS par tick pour qu'un tour de file entierement compose de taches
     * hors periode ne brule pas le budget en pur ordonnancement.
     *
     * Sous 1, le Sleep(1) de fin de tour DISPARAIT aussi. Ce n'est pas un oubli :
     * docs/philosophie_armes_egales dit que Sleep sert aux parties avec des HUMAINS, et qu'entre
     * IA on ne s'auto-handicape jamais -- AAAHogEx ne dort pas entre ses chunks. Rendre la main
     * alors qu'il reste du budget est exactement l'auto-handicap que ce principe interdit. Le
     * moteur suspend le script de lui-meme des que le budget du tick est epuise et le reprend au
     * tick suivant la ou il en etait : la boucle reste bornee et la partie avance normalement.
     * Sous 0, le Sleep(1) historique est conserve tel quel. */
    AddSetting({
      name = "loop_budget",
      description = "Drain the tick's opcode budget by running consecutive due tasks, with no end-of-turn sleep: 1 = drain (plays like AAAHogEx), 0 = one task then sleep (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Portefeuille v2. Revue du portefeuille, docs/taches.md S0 septies -- quatre soupcons
     * confirmes et deux trouvailles majeures, corriges ensemble parce qu'ils portent tous sur la
     * meme decision : quel projet unique est bati ce cycle.
     *
     * 0 (defaut, comportement historique) :
     *   - l'election modale par couple origine/destination se fait AVANT le test de capital, et sur
     *     `roi` qui est un RATIO : une ligne rail a 900 k£ bat une route a 45 k£ sur le meme
     *     couple, puis echoue faute de capital, et le couple ne rapporte alors RIEN ;
     *   - le sac a dos 0/1 maximise la somme des REVENUS, `profitAnnual` n'apparaissant nulle part
     *     dans l'objectif ;
     *   - `budgetScore` est un revenu par 1000 £ de capital, y compris dans le panneau IP| montre
     *     a l'operateur ;
     *   - deux projets finances ne peuvent partager aucune extremite, ce qui interdit la topologie
     *     en etoile que builder_air.nut produit -- sans rien apporter, puisque main.nut n'en batit
     *     qu'UN par cycle (maxBatch = 1) et regenere tout ensuite ;
     *   - le portefeuille n'est regenere qu'au changement de mois ou apres une construction
     *     reussie, capitalBudget fige a la generation : un mois ouvert a 60 k£ sans projet
     *     finançable ne construit RIEN de tout le mois, meme si la tresorerie monte a 400 k£.
     *
     * 1 : toutes les alternatives modales d'un couple sont conservees, le test de capital tranche,
     * le classement est le PROFIT par livre de capital mobilisable, le sac a dos est remplace par
     * « le meilleur projet finançable », et le portefeuille est regenere des que le capital
     * mobilisable a materiellement grandi. */
    /* Correctifs de flotte. Revue flotte et entretien, docs/taches.md S0 nonies -- trois defauts
     * qui visent tous le meme symptome mesure : 3,26 vehicules par gare contre 2,71 chez
     * AAAHogEx, et 8x moins de gares.
     *
     * 0 (defaut, comportement historique) :
     *   - rail_refleet est INJOIGNABLE. Son bloc (second train, passage en double voie, seuls
     *     sites d'appel de OpexBuildSecondTrain et OpexUpgradeRailLineToDoubleTrack) vit a
     *     l'interieur de _expandRailLines, derriere un return anticipe commande par rail_expand
     *     dont le defaut est 0 ; et _runNextTask desactive la tache definitivement sur le meme
     *     critere. Avec les defauts livres, AUCUNE ligne rail ne peut donc jamais gagner un second
     *     train ni une seconde voie -- alors que rail_refleet vaut 1 et est annonce actif.
     *   - toute ligne routiere neuve achete une seconde flotte complete dans son propre cycle de
     *     construction : vehCount n'est ecrit que par _reportLines, une fois par an, et la file
     *     execute projects puis refleet dans le meme cycle, donc la ligne arrive avec have = 0
     *     face a un target valant sa flotte reelle. OpexRoadRefleet saute alors la reprise de
     *     gabarit et cree un vehicule avec sa propre liste d'ordres avant de cloner le reste.
     *   - isAnyWaiting prend un vehicule en chargement pour un embouteillage. Sous
     *     OF_FULL_LOAD_ANY c'est l'etat normal d'un camion de fret, et les trois heuristiques de
     *     croissance exigent toutes !isAnyWaiting : la situation qui devrait declencher la
     *     croissance est lue comme une saturation. Le signal est inverse.
     *
     * 1 : les trois sont corriges. */
    /* Correctifs du modele economique. Revue de economy.nut, docs/taches.md S0 octies. Cible : le
     * rendement unitaire, mesure a -31,4 % contre AAAHogEx (6 332 £/an par vehicule net ajoute
     * contre 9 229 £).
     *
     * 0 (defaut, comportement historique) :
     *   - les seuils de note de ramassage valent 6,8 / 13,5 / 27 / 47 jours, alors que le source
     *     15.3 compare time_since_pickup a 3 / 6 / 12 / 21 CYCLES a ~2,5 jours le cycle, soit
     *     7,5 / 15 / 30 / 52,5. Chaque palier est ~10 % trop strict. Le plus couteux est le
     *     premier : TARGET_HEADWAY_DAYS = 7 tombe entre 6,8 et 7,5, donc le modele note sa PROPRE
     *     cible de conception a 95 points quand le moteur en accorde 130.
     *   - le nombre de convois est choisi au profit ABSOLU, sans jamais consulter roi ni capital,
     *     alors que c'est roi que le portefeuille classe ensuite. Ajouter un convoi augmente
     *     presque toujours le profit absolu et baisse le roi : le modele livre donc au portefeuille
     *     la variante la plus gourmande en capital de toutes celles qu'il a evaluees.
     *
     * ADOPTE AU BANC LE 2026-09-02 (docs/bench_isolation_3y_20seeds.json, 20 graines x 3 ans,
     * lecture appariee, reglage isole) : profit_year +21,1 % (t = 2,09, 14/20),
     * performance_history +16,1 % (t = 3,01, 15/20), company_value +11,7 % (t = 1,47, 12/20).
     * Les deux premieres depassent leur plancher de detection et priment sur company_value dans
     * l'ordre des objectifs du projet. Seule ombre : note de gare -5,9 % (t = -1,66), non etabli.
     *
     * 1 : les seuils suivent le source, l'ancre de calibration reste a 95 (voir economy.nut)
     * (le modele reproduit donc exactement STATION_RATING_PCT au headway de calibration, sans
     * constante nouvelle), et la variante est choisie sur le meme objectif que celui qui
     * l'arbitrera -- le profit par livre de capital. */
    /* Correctifs de pricing, decoupes en TROIS reglages pour que le banc puisse les isoler.
     * Groupes, ils ont ete mesures NUISIBLES le 2026-09-02 (docs/bench_pricing_3y_20seeds.json,
     * 20 graines x 3 ans) : company_value -14,8 %, profit_year -22,7 %, performance_history
     * -18,7 % (t = -3,82). Il reste a savoir lequel des trois porte la degradation.
     *
     * Hypothese principale : pricing_road_rating. La courbe de note a ete calibree sur des lignes
     * RAIL passagers (STATION_RATING_PCT = 50, mesure 49-55). L'appliquer a la route suppose qu'un
     * arret de bus se comporte comme une gare -- une ligne routiere courte y passe a 63,7 % au lieu
     * de 50 %, donc le modele devient PLUS optimiste et selectionne des lignes qui ne tiennent pas.
     * L'« incoherence » entre modes encodait peut-etre une mesure, pas un oubli. */
    AddSetting({
      name = "pricing_road_rating",
      description = "Apply OpexStationRatingForHeadway to road instead of a flat 50 percent: 1 = curve, 0 = flat (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Le depot rail manque au capital modelise, alors que builder_rail.nut le paie a chaque ligne
     * et que la route comme l'eau comptent le leur. C'est un cout REEL non compte : le seul des
     * trois dont la justesse ne fait aucun doute -- reste a voir ce que la mesure en dit. */
    AddSetting({
      name = "pricing_rail_depot",
      description = "Count the rail depot in modelled rail capital, as road and water already do: 1 = counted, 0 = omitted (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Erreur de dimension : les iterations d'un candidat ROUTE etaient facturees au tarif d'une
     * iteration du pathfinder RAIL (2 700 opcodes), ce qui double-comptait une planification deja
     * mesuree pendant la generation. */
    AddSetting({
      name = "pricing_road_ops",
      description = "Stop pricing road planning at the rail pathfinder rate: 1 = transaction cost only (default, adopted), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* La croissance urbaine cede le pas au portefeuille. docs/taches.md S0 septies et S0 decies.
     *
     * _tryTownGrowth construit des lignes de bus dont le candidat porte profitAnnual = 0 et
     * revenueAnnual = 0 EXPLICITES : son rendement est indirect (faire grossir la ville pour
     * nourrir les autres lignes), mais son capital est immediat et reel.
     *
     * Or le goulot mesure de cette IA est la VITESSE DU CAPITAL : 44,5 % de la valeur d'entreprise
     * dort en caisse contre 10,4 % chez AAAHogEx, et un seul projet est bati par mois. Une depense
     * a rendement predit nul entre donc en concurrence directe avec les projets rentables.
     *
     * 0 (defaut) : la croissance depense des qu'elle peut payer.
     * 1 : elle exige un surplus au-dela du capital que le portefeuille s'est deja engage a
     * depenser -- elle ne prend que ce dont il ne veut pas, sans jamais etre supprimee. */
    AddSetting({
      name = "growth_yields",
      description = "Town growth only spends capital the portfolio does not want: 1 = yields to funded projects, 0 = spends as soon as affordable (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_min_distance",
      description = "Minimum tile distance for a rail candidate. 25 = as shipped; 5 restores the rail/road overlap band that the file's own comments describe (see docs/taches.md 0 septdecies)",
      min_value = 5, max_value = 40,
      easy_value = 25, medium_value = 25, hard_value = 25,
      custom_value = 25,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_abandon",
      description = "Air build failures are remembered so the site scan stops re-proposing the same pair: 1 = remembered (default, adopted at bench, +6.1% company value on 18/20 seeds), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_margin",
      description = "Air authority margin applied per plan inside fleet sizing instead of shaving the global budget: 1 = per plan (default, adopted at bench as neutral-and-correct), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "economy_fix",
      description = "Source-verified station rating thresholds and train count chosen on profit per pound of capital: 1 = fixed (default, adopted at bench), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "fleet_fix",
      description = "Make rail_refleet reachable, stop new road lines from buying a second full fleet on their build cycle, and stop reading a loading vehicle as a jam: 1 = fixed, 0 = historical (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Plancher de profit ABSOLU du portefeuille v2, en pourcentage du meilleur profit finançable
     * du moment. N'a d'effet que sous portfolio_v2 = 1.
     *
     * POURQUOI IL EXISTE. Banc du 2026-09-02 (docs/bench_isolation_3y_20seeds.json, reglage
     * isole) : le tri au seul ratio profit/capital est le SEUL des quatre reglages a bouger le
     * volume -- 21,4 -> 27,2 gares, +27 % -- mais il coute -24,4 % de valeur et -30,7 % de profit
     * annuel. Un ratio favorise les tout petits projets bon marche, dont le profit absolu est
     * negligeable ; comme un seul projet est bati par cycle, chaque cycle est consomme par une
     * ligne mediocre et les gros projets rentables ne sont jamais atteints.
     *
     * Le plancher est RELATIF au meilleur projet finançable, donc independant de l'epoque, de la
     * taille de carte et de l'inflation. 0 reproduit exactement le comportement mesure ci-dessus ;
     * 100 ne garderait que le meilleur profit absolu. La valeur a retenir est a mesurer. */
    AddSetting({
      name = "portfolio_floor_pct",
      description = "Portfolio v2 only: minimum annual profit to be ranked, as a percentage of the best affordable project's profit. 0 = pure ratio ranking (default)",
      min_value = 0, max_value = 100,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 5,
      flags = 0
    });

    AddSetting({
      name = "portfolio_v2",
      description = "Portfolio selection on profit per pound of affordable capital, modal choice after the capital test, and regeneration when capital grows: 1 = v2, 0 = revenue knapsack, monthly only (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Nombre maximum de projets construits dans le meme passage du portefeuille. 1 conserve
     * exactement le passage historique : le premier succes regenere le portefeuille et arrete
     * la boucle. Les valeurs superieures ne reutilisent les plans figes qu apres revalidation
     * contre la carte et la tresorerie vivantes (main.nut). La borne 8 est volontairement petite :
     * mesure du 2026-09-02 sur docs/diag_vivier_3y.json (5 graines x 3 ans, defauts), le sac a dos
     * finance 203 projets pour 43 construits, mais la MEDIANE des portefeuilles n'en finance qu'UN
     * et le maximum observe est 14.
     *
     * MESURE, ET REGLAGE ECARTE (2026-09-02, docs/bench_portfolio_max_batch_3y.json, 20 graines
     * x 3 ans, apparie) : batch 4 contre 1 donne company_value -3,8 % (t = -1,77), profit_year
     * -4,8 %, n_stations -7,9 % (t = -2,04) et n_vehicles -9,5 % (t = -2,94). Test des signes :
     * 11 graines sur 20 sont des NULS EXACTS -- le batch ne se declenche jamais chez elles -- et
     * sur les 9 restantes le batch perd 6 fois contre 3 (p = 0,51 ; p = 0,11 sur le volume).
     *
     * POURQUOI C'EST NUL, verifie aux panneaux (docs/diag_batch8_5seeds.json) : un passage REUSSI
     * regenere lui-meme le portefeuille. Batir deux projets dans le meme passage ne fait donc pas
     * un chantier de plus, il FUSIONNE deux cycles en un -- le nombre de tentatives baisse au lieu
     * de monter (0/5 graines en hausse). Et meme a 8, le batch ne depasse jamais DEUX : la
     * tresorerie est videe entre-temps par les taches concurrentes (_tryBuildAir a son propre
     * batch de 3), le capital mobilisable tombant de 295 000 a 24 013 apres un seul chantier a
     * 26 589 £. Le plafond a 1 ne retenait rien ; le vrai goulot est la CONCURRENCE POUR LA CAISSE.
     *
     * Garde a 1 par defaut. Le reglage reste expose parce qu'il est le seul instrument capable de
     * remesurer ce plafond si la competition pour la tresorerie est un jour corrigee. */
    AddSetting({
      name = "portfolio_max_batch",
      description = "Maximum funded portfolio projects built in one pass. 1 = historical one-project behaviour (default); 2-8 = revalidated batch",
      min_value = 1, max_value = 8,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = 0
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

RegisterAI(OpexAIInfo());
