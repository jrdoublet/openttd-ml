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
   * abandon_memory, station_join et road_mode, eux, sont des parametres de conception exposes au banc,
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
     * /!\ RISQUE A NE PAS OUBLIER en abaissant ce seuil : rien dans le code ne REEMPRUNTE.
     * SetLoanAmount n'est appele qu'au demarrage (au maximum) et pour rembourser. Une compagnie
     * qui se desendette puis rencontre un candidat plus cher que sa tresorerie ne peut pas
     * reprendre l'emprunt -- elle renonce simplement a la ligne. C'est borne (le plancher couvre
     * la plus grosse ligne observee) mais c'est un vrai angle mort, a traiter separement.
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
     *   - Reste 1 graine (42) a 230 000 : une compagnie trop pauvre pour degager meme 300 000 de
     *     disponible. Descendre plus bas passerait sous le cout de la plus grosse ligne ; le vrai
     *     correctif pour ce cas est le reemprunt manquant ci-dessus. */
    AddSetting({
      name = "loan_repay_floor_k",
      description = "Cash floor below which the loan is not repaid, in thousands: 300 = measured default, 1000 = pre-2026-08-29 behaviour",
      min_value = 0, max_value = 2000,
      easy_value = 300, medium_value = 300, hard_value = 300,
      custom_value = 300,
      step_size = 50,
      flags = 0
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
     * DEFAUT REPASSE A 0 LE 2026-08-29, APRES MESURE. Le mecanisme marche : le vivier ne s'eteint
     * plus (graine 42, candidats classes 1984-89 de 0-3 a 4-28), les jointures ont lieu, et le
     * banc apparie sur 20 graines x 20 ans (docs/bench_v2_vivier.json) montre +37,2 % de vehicules,
     * t = 5,94, 18 graines sur 20, p = 0,0004. L'IA batit BEAUCOUP plus.
     *
     * Mais ca ne paie pas : company_value -0,3 % (t = -0,03, 9/20), performance_history +6,5 %
     * (t = 1,45, 11/20, sous le plancher de detection de ~12 %), variance explosee (de -54,8 % a
     * +330,5 % selon la graine) et emprunt non rembourse sur 4 graines contre 2. On construit plus
     * pour la meme valeur, en immobilisant plus de capital.
     *
     * LA CAUSE NOMMEE, non encore corrigee : OpexPaxCandidates/OpexFreightCandidates predisent le
     * debit d'une extremite DEJA servie avec sa production ENTIERE, en ignorant ce que la ligne
     * existante en prelevait deja (commentaire "BIAIS CONNU" dans candidates.nut). Un candidat a
     * jointure est donc sur-estime d'un facteur inconnu, et MIN_RATIO -- calibre sur des candidats
     * non joints -- ne le rattrape pas. Remettre le defaut a 1 demande d'avoir mesure ce facteur
     * (protocole sweeps/opex_predict_vs_actual.py sur les lignes jointes), pas avant. */
    AddSetting({
      name = "station_join",
      description = "Reuse one compatible nearby OpexAI rail station with a dedicated platform: 1 = enabled, 0 = historical too-close rejection",
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
     * 🔴 LE PRIX A CONNAITRE : une graine sur vingt (8675309) passe de 1 460 136 a **1**, c'est-a-
     * dire a l'insolvabilite, quand la route est active. Sa trajectoire diverge des 1974 : la
     * valeur s'erode de 165 793 a 55 691 en cinq ans pendant que le bras sans route grimpe, la
     * tresorerie finit collee au plancher CASH_RESERVE, et l'emprunt n'est jamais rembourse (sur
     * les DEUX bras -- cette graine appartient deja au regime d'echec d'emprunt connu). Mecanisme
     * NON etabli ; l'hypothese a tester est que la phase routiere consomme la tresorerie marginale
     * qui aurait finance la ligne rail suivante, et qu'une compagnie pauvre n'amorce alors jamais
     * sa composition. Ce n'est pas une raison de couper le mode -- 16 graines sur 20 gagnent -- mais
     * c'en est une de garder ce reglage, et de mesurer un plancher de tresorerie propre a la route
     * avant de considerer l'affaire close. */
    AddSetting({
      name = "road_mode",
      description = "Build short road lines (bus town-town, and truck freight industry-industry / industry-town): 1 = enabled, 0 = rail-only baseline",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
