class OpexAI extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA qui traite les opcodes comme une ressource de jeu : chaque candidat porte un profit attendu ET un cout en opcodes attendu, et le budget va au meilleur rapport."; }
  function GetVersion()     { return 3; }
  function GetDate()        { return "2026-08-28"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }

  /* Les reglages debug_signs et pathfinder_sleep_ticks existent pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains (loan_repay_floor_k, lui, est un parametre de conception
   * expose au banc, pas un bridage). Entre IA, la regle est l'inverse : jouer a armes egales,
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
