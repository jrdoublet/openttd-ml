class OpexAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA multimodale : meilleur ROI par origine/destination, puis revenu maximise sous contraintes de capital et d'opcodes."; }
  function GetVersion()     { return 7; }
  function GetDate()        { return "2026-09-09"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "13"; }

  /* Les reglages debug_signs et pathfinder_sleep_ticks existent pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains (loan_repay_floor_k, pathfinder_hard_cap_k,
   * abandon_memory, abandon_gen_filter, air_joined_stops, station_join, join_max_distance, join_place, origin_sitable, basin_share, reborrow, road_mode, road_pax_build, road_pax_catchment_pct, road_refleet, road_multistop, marginal_fleet, astar_cost, probe_negative et pax_near, eux, sont des parametres de conception exposes au banc,
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
      name = "decision_log",
      description = "Emit structured decision log lines via AILog: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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

    /* Symetrique de air_cost_probe : la route n'a jamais eu de sonde de cout reel equivalente
     * (docs/taches.md, retrouve le 2026-09-08). AIAccounting isole les vraies commandes de
     * OpexBuildRoadRoute -- aucun AITestMode interne, pas de bouclier necessaire. */
    AddSetting({
      name = "road_cost_probe",
      description = "Emit per-attempt road model capital versus actual cost (AIAccounting-isolated), including failed/rolled-back attempts: 1 = measurement only, 0 = no extra signs (default)",
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

    /* C15 : Relever la cadence d'agrandissement de flotte aerienne.
     * 7 = hebdomadaire (defaut), 90 = trimestriel, 365 = annuel/historique. */
    AddSetting({
      name = "air_fleet_cadence_days",
      description = "Delai minimal en jours entre deux extensions de flotte aerienne sur une meme ligne (7 = hebdomadaire, 90 = trimestriel, 365 = annuel, docs/taches.md C15)",
      min_value = 0, max_value = 365,
      easy_value = 7, medium_value = 7, hard_value = 7,
      custom_value = 7,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_presite",
      description = "Probe both airport sites in test mode before committing capital to the first one: 1 = enabled, 0 = build A then discover B (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* A7.2 : Vente immediate des convois de lignes mortes des leur arrivee au depot via
     * l'evenement ET_VEHICLE_WAITING_IN_DEPOT (1 = actif, 0 = classique/defaut). */
    AddSetting({
      name = "event_depot_sell",
      description = "Vente immediate des convois ferrailles des leur arrivee au depot via ET_VEHICLE_WAITING_IN_DEPOT (docs/taches.md A7.2): 1 = actif, 0 = cycle annuel classique (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* A7.1 : Stop-loss immediat sur fermeture d'industrie via l'evenement ET_INDUSTRY_CLOSE
     * (1 = actif, 0 = cycle annuel classique/defaut). */
    AddSetting({
      name = "event_industry_close",
      description = "Stop-loss immediat sur fermeture d'industrie via ET_INDUSTRY_CLOSE (docs/taches.md A7.1): 1 = actif, 0 = cycle annuel classique (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* A7.3 / C17 : Sonde subventions en lecture seule via AIEventSubsidy*
     * (1 = actif, 0 = inactif/defaut). */
    AddSetting({
      name = "event_subsidy_probe",
      description = "Sonde subventions en lecture seule via AIEventSubsidy* (docs/taches.md A7.3 / C17): 1 = actif, 0 = inactif (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* A7.4 : Alerte et diagnostic des convois perdus/bloques via ET_VEHICLE_LOST
     * (1 = actif, 0 = inactif/defaut). */
    AddSetting({
      name = "event_vehicle_lost",
      description = "Alerte et diagnostic des convois perdus/bloques via ET_VEHICLE_LOST (docs/taches.md A7.4): 1 = actif, 0 = inactif (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* P3 / A7.5 : Invalidation et rafraichissement reactif du catalogue via
     * ET_INDUSTRY_OPEN et ET_TOWN_FOUNDED (1 = actif par defaut). */
    AddSetting({
      name = "event_catalog_invalidate",
      description = "P3: rebuild catalog and portfolio immediately after an industry opens or a town is founded; 1 = enabled (default), 0 = monthly cycle only",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C39.0 : sonde sans changement de decision. Elle enregistre quelles couches un
     * futur invalidateur evenementiel aurait salies ; la cadence mensuelle et les decisions
     * existantes restent identiques quand elle vaut 0 (defaut). */
    AddSetting({
      name = "c39_invalidation_probe",
      description = "C39.0: log coalesced event invalidations without changing refreshes or decisions; 1 = probe, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C39.3 : exige c39_invalidation_probe=1 ; compare le top avant/apres rebuild et indique
     * si le moteur annonce a effectivement ete retenu par son sous-catalogue. */
    AddSetting({
      name = "c39_decision_delta_probe",
      description = "C39.3 probe: with c39_invalidation_probe=1, log catalog retention and top-project deltas; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C39.4 : explique les moteurs air non retenus, avec c39_invalidation_probe=1. */
    AddSetting({
      name = "c39_air_reason_probe",
      description = "C39.4 probe: with c39_invalidation_probe=1, log why an air engine was not selected; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C39.2 : consommer EngineAvailable par le scheduler historique, sans inclure les
     * industries déjà traitées par P3. Expérimental jusqu'au diagnostic apparié. */
    AddSetting({
      name = "c39_engine_refresh",
      description = "C39.2 experimental: rebuild catalog/portfolio after EngineAvailable; 1 = enabled, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.0 : registre de versions passif, qui exige la sonde C39 pour recevoir les evenements. */
    AddSetting({
      name = "c41_revision_probe",
      description = "C41.0 probe: with c39_invalidation_probe=1, log coalesced revisions and full-refresh acknowledgements; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.1 : demande aussi c39_invalidation_probe=1 et c41_revision_probe=1. */
    AddSetting({
      name = "c41_water_refresh",
      description = "C41.1 experimental: refresh only catalog.water after a water EngineAvailable; requires C39/C41 probes; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.2 : conserve C41.1 mesurable sans prefiltre ; demande aussi son reglage actif. */
    AddSetting({
      name = "c41_water_precheck",
      description = "C41.2 experimental: skip C41.1 for water engines not buildable/refittable to passengers; requires c41_water_refresh=1; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.3 : demande C41.1/C41.2 ; ne modifie aucun candidat ni portefeuille. */
    AddSetting({
      name = "c41_water_candidate_probe",
      description = "C41.3 probe: measure temporary OpexWaterPlans after C41.1/C41.2; requires c41_water_refresh=1; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.3a : attributer le cout de la sonde aux etapes physiques, sans changer son resultat. */
    AddSetting({
      name = "c41_water_plans_profile",
      description = "C41.3a probe: split temporary water-plan cost into sites, pairs, BFS and economics; requires c41_water_candidate_probe=1; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.3b : ne change que les compteurs internes au profile C41.3a. */
    AddSetting({
      name = "c41_water_site_profile",
      description = "C41.3b probe: split water site search into coastline filtering and test-mode dock commands; requires c41_water_plans_profile=1; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Reconstruction du BFS maritime sur MinchinWeb.Lakes (2026-09-09, docs/taches.md).
     * 1 = connectivite memorisee (un seul bassin explore par partie, sans marge de
     * bounding-box) + distance Manhattan pour le revenu (corrige un bug de tarification :
     * l'ancien code payait sur la distance navigable, pas la distance a vol d'oiseau entre
     * stations) + MinchinWeb.GetDockFrontTiles pour l'acces aux quais (pente reelle, pas un
     * scan aveugle des 4 cardinaux). 0 = comportement historique complet, bugs inclus --
     * conserve pour A/B, pas pour un usage courant. Un bug de regression (tuiles de quai
     * passees a Lakes au lieu des tuiles d'eau adjacentes) a ete trouve et corrige avant tout
     * banc ; smoke test + graine 24 (connue construire une ligne d'eau) revérifiés sains apres
     * correctif. Pas encore de banc officiel 20x10 apparie. */
    AddSetting({
      name = "water_lakes_connectivity",
      description = "Water BFS rebuilt on MinchinWeb.Lakes: 1 = memorised basin connectivity + correct Manhattan revenue distance + slope-aware dock access (default), 0 = historical BFS-only behaviour (kept for A/B)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.11 : audit annuel du budget perdu par le scheduler historique, sans le modifier. */
    AddSetting({
      name = "c41_slack_ledger",
      description = "C41.11 probe: aggregate scheduler task opcode use and initial slack annually; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_monthly_busy_ledger",
      description = "C41 probe: monthly opcode attribution by scheduler task; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.12 : ages par couche, seulement au moment d'un acquittement effectif. */
    AddSetting({
      name = "c41_staleness_ledger",
      description = "C41.12 probe: log coalesced staleness age for each layer when actually acknowledged; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.13 : combien de reliquat le scheduler historique laisse aux couches encore stale. */
    AddSetting({
      name = "c41_opportunity_ledger",
      description = "C41.13 probe: aggregate opcode slack observed while each C41 layer remains stale; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.14 : pilote d'admission, aucune tache supplementaire n'est executee ici. */
    AddSetting({
      name = "c41_admission_ledger",
      description = "C41.14 probe: count stale targeted-catalog microtasks that fit their declared opcode hint; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.15 : invalide seulement le materiel route, pas les candidats derives. */
    AddSetting({
      name = "c41_road_refresh",
      description = "C41.15 experimental: refresh only catalog.road after a road EngineAvailable; requires C39/C41 probes; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.16 : aucune regeneration supplementaire, seulement une ventilation de la passe normale. */
    AddSetting({
      name = "c41_road_candidate_profile",
      description = "C41.16 probe: split normal road-candidate generation into pax, freight, feeder and TopK opcodes; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.17 : sous-ventilation uniquement ; elle implique implicitement le profil route. */
    AddSetting({
      name = "c41_road_freight_profile",
      description = "C41.17 probe: split freight road candidates into preparation, industry sinks and town sinks opcodes; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.18 : index valide par le banc appaire officiel 20x10 ; les sondes restent separees. */
    AddSetting({
      name = "c41_road_freight_served_index",
      description = "C41.18: index served rail/road origins for freight road candidates; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_road_freight_town_profile",
      description = "C41.19 probe: count and time freight town acceptance and economics calls; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_road_freight_acceptance_index",
      description = "C41.20: preindex full-acceptance towns by freight cargo; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_road_feeder_profile",
      description = "C41.21 probe: split feeder generation in road build and fresh portfolio injection; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_portfolio_profile",
      description = "C41.22 probe: split rail generation, prequote, portfolio insertion and selection opcodes; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_candidate_profile",
      description = "C41.23 probe: split normal rail candidates into pax, freight and TopK opcodes; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_profile",
      description = "C41.24 probe: split rail pax preparation, town-pair scan and candidate calls; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_candidate_profile",
      description = "C41.25 probe: split rail pax candidate calls into origin sitability and economics; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_economics_profile",
      description = "C41.26 probe: split rail pax economics into setup, train loop and finalization; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_speed_profile",
      description = "C41.27 probe: measure effective-speed calls inside rail pax economics; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_speed_detail_profile",
      description = "C41.28 probe: split rail pax speed into cruise, acceleration and integration; count exact reusable keys; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_cruise_profile",
      description = "C41.29 probe: count exact reusable cruise keys (loco, wagon, wagons) in rail pax economics; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_pax_cruise_cache",
      description = "C41.30: cache rail pax cruise speed by (loco, wagon, wagons) within one candidate generation; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_freight_profile",
      description = "C41.31 probe: split rail freight generation into preparation, industry and town sinks; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_freight_candidate_profile",
      description = "C41.32 probe: split rail freight pair guards from candidate economics; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c41_rail_freight_economics_profile",
      description = "C41.33 probe: measure rail freight candidate economics; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({ name = "c41_rail_freight_economics_detail_profile", description = "C41.34 probe: split rail freight economics; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_economics_setup_profile", description = "C41.35 probe: split freight economics setup into reference, consist and capital; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_economics_consist_profile", description = "C41.36 probe: split freight consist sizing speed calls and residual; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_cruise_profile", description = "C41.37 probe: count exact reusable freight cruise keys; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_cruise_cache", description = "C41.38: cache freight cruise speed by (loco, wagon, wagons) within one candidate generation; 1 = on (default), 0 = off", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_speed_detail_profile", description = "C41.39 probe: split freight effective speed into acceleration and integration; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_acceleration_cache", description = "C41.40: cache freight acceleration within one candidate generation; 1 = on (default), 0 = off", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_effective_speed_profile", description = "C41.41 probe: count exact reusable freight effective-speed keys; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_town_guards_profile", description = "C41.42 probe: measure freight industry-to-town guards; 1 = on, 0 = off (default)", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "c41_rail_freight_town_service_cache", description = "C41.44: cache freight town service within one candidate generation; 1 = on (default), 0 = off", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN });

    /* C41.4 : inventaire passif des vehicules perdus, independant de l'alerte A7.4. */
    AddSetting({
      name = "c41_vehicle_lost_probe",
      description = "C41.4 probe: log VehicleLost line/mode/orphan attribution only; no repair, no scheduling; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.5 : cause observable d'un Lost rail, sans inferrer un blocage de signal. */
    AddSetting({
      name = "c41_rail_lost_probe",
      description = "C41.5 probe: log rail Lost order, position and depot facts only; no repair or scheduling; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.6 : attributs topologiques déjà persistés d'une ligne rail perdue. */
    AddSetting({
      name = "c41_rail_lost_topology_probe",
      description = "C41.6 probe: log persisted rail Lost topology only; no map scan, repair or scheduling; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.7 : sondage local des sorties de quai et fronts de depot d'un Lost rail. */
    AddSetting({
      name = "c41_rail_lost_physical_probe",
      description = "C41.7 probe: log local rail approaches and depot fronts only; no path search, repair or scheduling; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.8 : reparation PBS uniquement, sur les approches simples d'une ligne double perdue. */
    AddSetting({
      name = "c41_rail_lost_signal_repair",
      description = "C41.8 experimental: after rail VehicleLost, add PBS only on eligible single-track approaches; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.9 : connectivite locale des approches et depots d'un Lost rail. */
    AddSetting({
      name = "c41_rail_lost_connectivity_probe",
      description = "C41.9 probe: log local rail branch connectivity after VehicleLost; no path search, repair or scheduling; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.10 : repare le seul raccord quai/depot->voie manquant trouve par C41.9 (une branche
     * candidate non ambigue seulement), sous AITestMode d'abord puis commande reelle seulement
     * si ce meme raccord reussit en test. */
    AddSetting({
      name = "c41_rail_lost_junction_repair",
      description = "C41.10 experimental: after rail VehicleLost, repair one unambiguous missing local rail junction under AITestMode then for real only if the same junction succeeds; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.46 : le ledger C41.11 etiquette toute la passe "rail_search" des que _railSearch est
     * non nul en entree, mais _runNextTask avance une tranche A* PUIS execute une tache de file
     * dans le MEME passage (main.nut, commentaire A4) -- les deux cout sont donc agreges. Cette
     * sonde encadre isolement le seul appel _continueRailSearch() pour separer : opcodes nets de
     * la tranche A*, opcodes de la tache de file dans la meme passe, iterations cumulees de
     * l'annee, et le nombre de tranches qui n'ont PAS atteint slice.done (recherche encore en
     * cours apres l'appel) contre celles qui l'ont atteint. Aucun dueCycle, aucune borne, aucune
     * decision modifiee -- purement observatoire (docs/04_arbitrage_rail_search.md). */
    AddSetting({
      name = "c41_rail_slice_ledger",
      description = "C41.46 probe: separate net rail A* slice opcodes from same-pass task opcodes and count slices that did not reach slice.done; no scheduling change; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C41.47 : pendant exact de la garde G3S1 (plan en echec), applique au second motif de
     * blocage -- la tresorerie. _consumeRailSearch() laisse aujourd'hui _railSearch non nul
     * indefiniment tant que money < need, ce qui bloque _expandRailLines (main.nut:4445, "ne
     * pas empiler une seconde recherche") ET tout autre candidat rail du portefeuille
     * (_tryBuildRailProject, reason=search_in_progress) -- pas seulement le candidat bloque.
     * N=0 (liberation immediate, comme G3S1) : des le premier blocage tresorerie constate
     * (pre-verification OU echec CASH a l'execution du plan), _railSearch est libere.
     * candidate.railPlan N'EST PAS efface : la revalidation en resulte gratuitement, car
     * OpexBuildLine reutilise deja un railPlan existant sans replanification (la meme
     * absence de revalidation que le chemin actuel de nouvelles tentatives sur cash) --
     * voir docs/04_arbitrage_rail_search.md pour l'analyse complete. Aucun changement de
     * dueCycle, aucune priorite touchee -- correctif de blocage, pas un arbitrage. */
    AddSetting({
      name = "c41_rail_cash_release",
      description = "C41.47: release _railSearch immediately when the only reason build() cannot proceed is insufficient cash, so other rail candidates and _expandRailLines are no longer blocked; the pending railPlan is kept on the candidate for reuse; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C43/E3 famille 2 : CASH_RESERVE_MIN mord-il ? Compteurs cumulatifs, publies en delta annuel
     * par la tache "report" (OpexCashReserve() est appelee trop souvent pour journaliser chaque
     * appel). */
    AddSetting({
      name = "cash_reserve_probe",
      description = "C43/E3 probe: count CASH_RESERVE_MIN/MAX binds in OpexCashReserve() per year; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C43/E3 famille 2 : PORTFOLIO_REFRESH_MIN_GAIN mord-il independamment du doublement (l'autre
     * moitie de la condition ET du rafraichissement "capital") ? Compteurs cumulatifs, delta
     * annuel par "report", meme schema que cash_reserve_probe. */
    AddSetting({
      name = "portfolio_refresh_probe",
      description = "C43/E3 probe: count PORTFOLIO_REFRESH_MIN_GAIN vs doubling threshold checks per year; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* D3.1 : Filtre eliminatoire ratio_too_low dans le vivier
     * (1 = actif/defaut historique, 0 = inactif, preserve les candidats a profit>0). */
    AddSetting({
      name = "vivier_ratio_filter",
      description = "Filtre eliminatoire opcodeRatio < minRatio dans le vivier (docs/taches.md D3.1): 1 = actif (defaut), 0 = desactive",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C14 : Desserrer le gain de la boucle de croissance aerienne
     * (-1 = inactif, >=0 = tampon de cargo au sol avant achat proportionnel).
     * ADOPTE a 0 le 2026-09-04 (docs/taches.md, 0 septquadragesies) : balayage factoriel
     * 18 bras x 20 graines x 10 ans (results/bench_c14_c15_trajectory_10y.json) montre que la VALEUR
     * du tampon est indifferente (0 = 50 = +40 % de profit) -- seul le fait d'armer le mecanisme
     * compte. buffer=0 est donc le bras le plus simple qui capte le gain : +40,4 % de profit a
     * 10 ans, 17/20 graines, p=0,002. */
    AddSetting({
      name = "air_fleet_buffer",
      description = "Tampon de cargo en attente avant achat proportionnel d'avions (docs/taches.md C14): -1 = inactif, >=0 = taille du tampon (defaut 0, adopte 2026-09-04)",
      min_value = -1, max_value = 500,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 5,
      flags = 0
    });

    /* C26a : Pricer l'avion de la ligne (fleet_fix n°5)
     * (docs/taches.md C26a) : price le modele reellement exploite sur la ligne plutot que le meilleur du catalogue. */
    AddSetting({
      name = "air_fleet_line_price",
      description = "Price le modele d'avion de la ligne lors du refleet au lieu du catalogue (docs/taches.md C26a): 1 = actif (defaut), 0 = inactif",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* D3.2 : Assainissement de profit_non_positive via le taux d'amortissement de l'infrastructure
     * (docs/taches.md D3.2). Dans OpenTTD, l'infrastructure ne s'amortit pas dans les comptes ;
     * deduire 1/30e du capital infra par an de profitAnnual rejette des candidats rentables sous
     * profit_non_positive. Valide au banc 20 graines x 10 ans (results/bench_d3_2_infra_amort_10y_20seeds.json) :
     * valeur moyenne +10,0 % (t = +2,09, p < 0,05), profit annuel moyen +10,5 % (14 victoires sur 20 graines).
     * Defaut adopte a 0 (zero amortissement fictif d'infrastructure). */
    AddSetting({
      name = "infra_amort_pct",
      description = "Pourcentage d'amortissement annuel de l'infrastructure (voies/gares) dans profitAnnual (docs/taches.md D3.2): 0 = reel OpenTTD (adopte), 100 = defaut historique",
      min_value = 0, max_value = 100,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 10,
      flags = 0
    });

    /* E10 : Correctif du doublement de flotte routiere au cycle de construction
     * (docs/taches.md E10) : empeche refleet de voir have=0 et de doubler la flotte neuve. */
    AddSetting({
      name = "road_fleet_fix",
      description = "Empeche le doublement de flotte routiere au cycle de construction (docs/taches.md E10): 1 = actif (adopte), 0 = inactif (defaut historique)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C16 : Plafond physique de flotte aerienne derive de la cadence d'absorption de la piste
     * (docs/taches.md C16) : derive de la rotation aller-retour et du stationDateSpan par type d'aeroport. */
    AddSetting({
      name = "air_cadence_cap",
      description = "Plafond physique de flotte aerienne par la cadence de piste (docs/taches.md C16): 1 = actif (defaut), 0 = inactif",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C26b : Correctif du faux embouteillage lorsque le vehicule est a quai en chargement (fleet_fix n°4)
     * (docs/taches.md C26b) : sans MARGINAL_FLEET, autoriser le refleet routier degrade le profit
     * de -17,6 % a 10 ans en empilant jusqu'a 16 camions sur des arrets a un seul quai. Defaut a 0. */
    AddSetting({
      name = "road_loading_fix",
      description = "Ignore les vehicules a quai pour la detection d'embouteillage routier (docs/taches.md C26b): 1 = actif, 0 = inactif (defaut confirme)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C27 : Sortir les bonus du numerateur de densite (fret monopole/chaine, feeder reseau)
     * pour retablir l'equite modale face a l'aerien dans budgetScore/opcodeScore (docs/taches.md C27).
     * Valide au banc (results/diag_c27_feeders.json): valeur mediane +17.8%, profit median +26.4%,
     * feeders vers aeroports en hausse (+13.5%, 37 -> 42), lignes air +47.1% (87 -> 128). Defaut 1. */
    AddSetting({
      name = "clean_density_score",
      description = "Sort les bonus du numerateur de densite du portefeuille pour retablir l'equite modale (docs/taches.md C27): 1 = densite brute (adopte), 0 = bonus historiques au numerateur",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C28 : Maximum glissant sur les N derniers cycles pour capitalCeiling (docs/taches.md C28).
     * Supprime le cliquet infini sans decroissance (mesure fige a 295 000 £), qui continue
     * d'admettre au vivier des projets inaccessibles quand la compagnie s'appauvrit.
     * 0 = cliquet infini historique (sans decroissance) ; N > 0 = maximum glissant sur les N
     * derniers cycles/regenerations. Valide au banc 10 ans : N=24 donne +13.7% valeur mediane,
     * +4.7% valeur moyenne, 3/5 gains et 0 defaite. Defaut 24 (~2 ans). */
    AddSetting({
      name = "capital_ceiling_cycles",
      description = "Fenetre glissante en cycles pour capitalCeiling (docs/taches.md C28): 0 = cliquet infini historique, N > 0 = max glissant sur N cycles (defaut 24)",
      min_value = 0, max_value = 120,
      easy_value = 24, medium_value = 24, hard_value = 24,
      custom_value = 24,
      step_size = 1,
      flags = 0
    });

    /* C29.1 + C29.2 : Deverrouillage du rabattement (feeders) vers hubs aeriens et ferroviaires (docs/taches.md C29).
     * C29.1 : Hubs restreints aux modes lourds passagers (Air + Rail Pax). Fret pur (charbon, fer) et bus exclus.
     * C29.2 : Une ville n'est plus bloquee par une ligne de bus ordinaire ; seul un feeder existant vers CE hub l'exclut.
     * 1 = actif (deverrouille), 0 = historique. */
    AddSetting({
      name = "feeder_unlock",
      description = "Deverrouille le rabattement vers les hubs (docs/taches.md C29.1 et C29.2): 1 = actif, 0 = historique",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C29.3 : Pricing du feeder calculé sur le revenu hub et le bassin de captage (docs/taches.md C29.3).
     * Prix = revenu de la ligne du hub * part de captage (repli 78 %). Prevention du double compte.
     * 1 = pricing calcule (defaut), 0 = bonus forfaitaire historique x1.60. */
    AddSetting({
      name = "feeder_pricing",
      description = "Pricing du feeder selon revenu hub et part captee (docs/taches.md C29.3): 1 = calcule (defaut), 0 = bonus x1.60",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C32 : LES FEEDERS REVIENNENT AU PORTEFEUILLE (docs/taches.md C32).
     * C29.3 les avait sortis d'OpexBuildRoadCandidates pour deux motifs, tous deux traites ici :
     * la collision de cle OD (ils ont desormais leur propre espace de cles, prefixe "feeder|" dans
     * OpexProjectKeyFor, donc ils n'evincent plus l'aerien via OpexProjectModeBetter) et
     * l'ecrasement par l'opcodeScore aerien -- qui est precisement ce que l'arbitrage doit
     * trancher, pas contourner. Sous 1, la tache dediee _tryBuildFeeders est eteinte : la laisser
     * active batirait la meme ligne deux fois.
     * 1 = arbitre au portefeuille (defaut), 0 = tache dediee hors arbitrage (comportement C29). */
    AddSetting({
      name = "feeder_portfolio",
      description = "Rabattement arbitre au portefeuille au lieu d'une tache dediee (docs/taches.md C32): 1 = portefeuille (defaut), 0 = tache dediee",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Les aeroports construisent deja leurs arrets de captage joints (`air_joined_stops`) ; la
     * generation historique de lignes bus ville->hub est donc exclue par defaut. Le bras 1
     * demeure disponible pour rejouer cette strategie explicitement au banc. */
    AddSetting({
      name = "feeder_candidates",
      description = "Generate new town-to-hub feeder bus candidates: 0 = disabled by default; airport joined stops remain active, 1 = legacy feeder candidate strategy",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C34.1 : CONSTRUCTION AERIENNE ARBITREE PAR LE PORTEFEUILLE (docs/taches.md C34).
     * Motif mesure (0 novemquinquagesies) : OpexAirPlans etait appele DEUX fois par cycle, une fois
     * par la tache dediee (main.nut:971) et une fois par le portefeuille (projects.nut:693), et
     * chaque passage coute ~21 jours de temps de jeu. Sur la graine 1, ONZE passages ont mange 63 %
     * de l annee 1. Eteindre la tache dediee supprime la moitie du goulot, et l executeur du
     * portefeuille sait deja batir mode == "air".
     * 1 = portefeuille seul (defaut), 0 = tache dediee _tryBuildAir en plus. */
    AddSetting({
      name = "air_portfolio",
      description = "Construction aerienne arbitree par le portefeuille seul (docs/taches.md C34.1, C36.2): 1 = portefeuille (adopte C36.2, +4,4 % valeur, +6,2 % profit, +36 pts score a 3 ans), 0 = tache dediee",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C34.2 / C36.2 : CROISSANCE DE FLOTTE ARBITREE PAR LE PORTEFEUILLE (docs/taches.md C36.2).
     * La tache air_fleet passait AVANT `projects` dans l ordre de service : elle avait un droit de
     * tirage sur la tresorerie et etait servie d office avant toute ligne neuve. Sous 1, elle
     * tourne en MODE A BLANC (_resizeAirFleets(year, plan)) et injecte les achats au portefeuille.
     * 1 = portefeuille (defaut C36.2), 0 = tache dediee servie en premier. */
    AddSetting({
      name = "fleet_portfolio",
      description = "Croissance de flotte aerienne arbitree par le portefeuille (docs/taches.md C34.2, C36.2): 1 = portefeuille (adopte C36.2), 0 = tache dediee",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* A1 : CLASSEMENT PAR VECTEUR DE TENSION (docs/taches.md A1, Option A).
     * Remplace le denominateur budgetCapital par la tension totale adimensionnelle de Liebig :
     *   TensionTotale = T_argent + T_slots + T_opcodes + T_foncier + T_decision
     *   Score = ProfitAnnuel * 1000 / TensionTotale
     * En regime pauvre, T_argent domine et la fonction degenere en ROI du capital.
     * En regime riche, T_argent s'efface devant T_decision et le score maximise le PROFIT ANNUEL brut.
     * En saturation de flotte, T_slots domine et le score maximise le PROFIT PAR VEHICULE.
     * 1 = actif, 0 = classement historique sur budgetScore / ROI (defaut). */
    AddSetting({
      name = "tension_scoring",
      description = "Classement du portefeuille par vecteur de tension (docs/taches.md A1 Option A): 1 = tension de Liebig, 0 = budgetScore historique",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C35.5 : FRICTION DE DECISION DU CLASSEMENT CONTINU (docs/taches.md C35.5).
     * Denominateur = friction + sum_r T_r(projet).
     * En pour mille : 50 = 0.05 (defaut A1), 10 = 0.01, 0 = 0.0. */
    AddSetting({
      name = "decision_friction_permille",
      description = "Friction de décision en pour mille (C35.5): 50 = 0.05 (défaut A1), 10 = 0.01, 0 = 0.0",
      min_value = 0, max_value = 1000,
      easy_value = 50, medium_value = 50, hard_value = 50,
      custom_value = 50,
      flags = 0
    });

    /* C35.3/C35.4 : COÛT RÉDUIT À PRIX D'OMBRE DUAL.
     * Score = ProfitAnnuel - Σ_r λ_r a_ir pour les contraintes tendues sur le
     * vivier (λ_r > 0). Si k>1 le prélèvement est partagé. Complementary
     * slackness = propriété de la ressource, pas de la taille du projet.
     * 1 = actif, 0 = inactif (défaut). */
    AddSetting({
      name = "shadow_pricing",
      description = "Coût réduit à prix d'ombre dual coordonné (docs/taches.md C35.4): 1 = actif, 0 = inactif (défaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C32 : SUPPRESSION DES BONUS FORFAITAIRES DE CLASSEMENT (docs/taches.md C32).
     * Le fret portait jusqu'a x1,89 sur son roi (monopole x1,40 puis chaine x1,35) et un feeder
     * x1,60 forfaitaire. Un forfait n'est pas une estimation : il deplace le classement sans rien
     * predire, et C27 avait deja du le sortir du numerateur de densite parce qu'il faussait un
     * diagnostic entier. Une fois feeder_pricing en place, aucun mode n'a besoin de forfait.
     * 0 = aucun bonus forfaitaire (defaut), 1 = forfaits historiques. */
    AddSetting({
      name = "flat_bonus",
      description = "Bonus forfaitaires de classement fret x1.89 et feeder x1.60 (docs/taches.md C32): 0 = supprimes (defaut), 1 = historiques",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* C29.4 : Couverture multi-arrêts urbaine pour rabattement (docs/taches.md C29.4).
     * Jusqu'à ceil(maisons / ROAD_STOP_CATCHMENT_HOUSES) gares distinctes par ville (modèle AAAHogEx).
     * 1 = active (defaut), 0 = arret unique historique par ville. */
    AddSetting({
      name = "feeder_town_coverage",
      description = "Couverture multi-arrets urbaine rabattement (docs/taches.md C29.4): 1 = active (defaut), 0 = arret unique",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C29.5 : Duplication des bus de rabattement passagers par des camions postaux (docs/taches.md C29.5).
     * Double la flotte de rabattement sur l'infrastructure existante (modele AAAHogEx #M1).
     * 1 = actif (defaut), 0 = desactive. */
    AddSetting({
      name = "feeder_mail_duplicate",
      description = "Double les bus de rabattement avec des camions postaux (docs/taches.md C29.5): 1 = actif (defaut), 0 = desactive",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_max_distance",
      description = "Plafond de distance pour les liaisons aeriennes (0 = illimite/defaut, docs/taches.md C6)",
      min_value = 0, max_value = 1000,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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

    /* C43/E3 : sature a 77,4%/70,1% des appels de selection (results/diag_constants_binding_6y_5seeds.json,
     * 2026-09-08) -- mord fort. Jamais retouche depuis 2026-09-02 avant cette mesure ; expose pour
     * le banc factoriel 32 contre 64. */
    AddSetting({
      name = "project_top_k",
      description = "Taille de la fenetre de selection du portefeuille (64 = defaut mesure, 2026-09-08 : sature a 70-77% des appels)",
      min_value = 8, max_value = 128,
      easy_value = 64, medium_value = 64, hard_value = 64,
      custom_value = 64,
      step_size = 8,
      flags = 0
    });

    /* Propose par l'utilisateur le 2026-09-08 : caler la fenetre sur villes+industries de la
     * carte (borne 16-128) au lieu de project_top_k fixe. Inerte a 0 (defaut). */
    AddSetting({
      name = "project_top_k_dynamic",
      description = "Cale PROJECT_TOP_K sur (villes + industries) de la carte, borne 16-128, au lieu du reglage fixe project_top_k: 1 = dynamique, 0 = fixe (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "feeder_enabled",
      description = "Tache dediee de rabattage bus vers les hubs aeriens/ferroviaires (docs/taches.md C1): 1 = active (defaut), 0 = desactive",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Conditionnement des feeders au besoin reel du hub (evite construction prematuree ou redondante) :
     * 1 = actif (attend maturite du hub et stock insuffisant, defaut), 0 = aveugle immediat. */
    AddSetting({
      name = "feeder_hub_check",
      description = "Condition feeder build on hub need: 1 = active (require hub maturity and low waiting stock, default), 0 = blind build",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Seuil max de passagers en attente au hub pour autoriser un feeder (au-dela, le hub est sature). */
    AddSetting({
      name = "feeder_hub_wait_max",
      description = "Max hub waiting passengers to allow feeder (above this, hub is already saturated)",
      min_value = 0, max_value = 1000,
      easy_value = 100, medium_value = 100, hard_value = 100,
      custom_value = 100,
      step_size = 10,
      flags = 0
    });

    /* Age minimum (en jours) de la ligne du hub avant d'autoriser la construction d'un feeder. */
    AddSetting({
      name = "feeder_hub_min_days",
      description = "Minimum days of hub line operation before building feeder",
      min_value = 0, max_value = 365,
      easy_value = 60, medium_value = 60, hard_value = 60,
      custom_value = 60,
      step_size = 5,
      flags = 0
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
     * CE QUE LA MESURE DU 2026-08-29 REPROCHE A CETTE VALEUR (results/opexai_emprunt.json, 6 graines
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
     * VERDICT DU BANC APPARIE (results/bench_v2_emprunt.json, 20 graines x 20 ans, OpexAI contre
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
     *     (results/opex_reborrow_20y_42.json). Descendre le plancher sous 300 passerait sous le
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
     * VERDICT (5 graines x 20 ans, results/opex_reborrow_20y_42.json et
     * results/opex_reborrow_20y_4seeds.json) : 412 GC, 0 tirage, 0 GC avec de l'emprunt encore
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
     * (results/opex_attempt_distance_20y_5seeds.json). ATTEMPT_MULTIPLIER reste 4 :
     * p95(iter OK)/amort <= 2,7. Le plancher 2000 absorbe le court.
     *
     * 5 graines (results/opex_astar_cost1_20y_5seeds.json) : on construit encore
     * (13-20 lignes), mediane 51->47 tuiles, tentatives et ABND baissent.
     * Le piege "budgets 50-400, zero ligne" est evite.
     *
     * VERDICT n=20 (results/bench_astar_cost.json) : company_value -8,9 %, t = -1,86,
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
     * POURQUOI CES BORNES. Sondage a 40 000 iterations (results/opex_probe_negative_hardcap_20y_5seeds.json) :
     * 11/11 pax <=100 rentables en derniere annee (predit -146..-9, reel 10-20 k) ;
     * >100 tuiles, mediane reelle 0. Lever le filtre partout readmettrait le long
     * du vivier. -200 couvre l'echantillon sans ouvrir le gouffre.
     *
     * VERDICT n=20 (results/bench_pax_near.json) : company_value +0,6 %, t = 0,10,
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
      description = "Resume rail A* across task-queue turns so other tasks run during a long search (docs/taches.md A4): 1 = sliced (default, adopted), 0 = blocking",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* C20 : Echeance de securite par micro-etape (tranche) au lieu d'une echeance globale.
     * En mode rail_search_resumable=1, l'echeance historique etait posee UNE FOIS au demarrage
     * (RAIL_SEARCH_SAFETY_TICKS = 54020). Partagee avec les autres taches, elle expirait et
     * tuait la recherche en DEAD (-27,5 % de gares, §0 undecies sexies).
     * Si 1, chaque micro-etape porte sa propre echeance de securite locale. Defaut 1 (adopte). */
    AddSetting({
      name = "rail_micro_deadline",
      description = "Echeance de securite par micro-etape pour la recherche reprenable (0 = globale historique, 1 = par tranche, C20, defaut adopte)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Pathfinding segmente (docs/taches.md A5). Sonde 2026-09-03 : 40 % des tentatives
     * rail meurent en ABND. A3 a plafonne a 10k, donc l'objectif n'est plus d'accelerer
     * les succes mais de convertir les abandons. Port de TrainLineAI-segmented.
     * Banc 20 graines x 10 ans (results/bench_rail_segmented_10y.json) : le mecanisme
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

    /* C33.3 : Delai de reprise sur la memoire d'abandon au lieu d'un bannissement definitif.
     * Si > 0, les paires abandonnees sont expirees apres (abandon_cooldown_days * echecs) jours.
     * Defaut 365 (adopte ; 0 = bannissement permanent historique). */
    AddSetting({
      name = "abandon_cooldown_days",
      description = "Delai de reprise en jours sur la memoire d'abandon (365 = defaut adopte, 0 = permanent historique, >0 = cooldown lineaire avec backoff, docs/taches.md C33.3)",
      min_value = 0, max_value = 5000,
      easy_value = 365, medium_value = 365, hard_value = 365,
      custom_value = 365,
      step_size = 30,
      flags = 0
    });

    /* C22 : Filtrer les paires abandonnees des la generation des candidats plutot qu'a l'arbitrage
     * du portefeuille. Evite que les paires vouees a l'echec n'occupent des slots TOP_K et n'evincent
     * des projets viables (89 % des rejets vivier etaient des abandoned_pair, docs/taches.md C22). */
    AddSetting({
      name = "abandon_gen_filter",
      description = "Appliquer les paires abandonnees comme filtre rail/route/feeders (generation, portefeuille et execution ; 1 = filtre actif, defaut adopte ; 0 = memoire de diagnostic sans exclusion, docs/taches.md C22)",
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
     *   - avant traction (results/bench_v2_vivier.json) : vehicules +37,2 %, t = 5,94, 18/20 ;
     *     company_value -0,3 %, t = -0,03 ;
     *   - apres traction (results/bench_join_after_traction.json) : vehicules +23,6 %, t = 3,50,
     *     17/20 ; gares -11,9 %, t = -3,61 (reemploi du StationID) ; company_value +5,9 %,
     *     t = 0,96, 11/20 -- sous le plancher ~15 %. Sans la graine 1337 (+132 %) il reste
     *     +1,6 %, t = 0,34. On construit plus, sur moins de gares, pour la meme valeur.
     *
     * CE QUI N'EST PAS LA CAUSE. Le double comptage de monthly a une origine servie a ete mesure
     * (results/opex_join_bias.json) et, une fois type, distance et epoque neutralises, son intervalle
     * contient 1. Corriger monthly sur ce chiffre brut serait le piege deja desamorce.
     *
     * SUITE : basin_share a ete mesure, defaut 0, et ne paie pas (les jointures sont
     * declassees, l'IA repose des gares neuves). Le spread n'est PAS la suite : il
     * convertirait des NOPLAN en jointures sur un classement qui ne paie pas.
     * docs/aaahogex_rail_join.md reste la note d'idees, pas un plan.
     *
     * REFUS (2026-08-30). OB|R decompose le null : 196 M, 75 K, 0 R, 41 other, 705
     * tentatives, 39 OK, 0 JOINPATH (results/opex_join_refuse_20y_5seeds.json). R meurt
     * a la generation. JOINPATH est vide. Les echecs sont SITEA/SITEB.
     *
     * RENDEMENT (2026-08-30). OpexJoinPlatformPlans cherche offset 1-4, pas le spread.
     * 39 -> 71 OK (5,5 % -> 15,7 %), SITE 692 -> 393, 361 nClear=0 restants au quai
     * joint (results/opex_join_parallel_20y_5seeds.json). 5/5 plus de vehicules, 4/5
     * moins de valeur. Le spread n'est pas la suite.
     *
     * H1 (2026-08-30). Population encore longue (results/opex_join_pop.json).
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
     * Valeur de travail 50 (results/opex_join_pop.json) : jointures <50 tuiles
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
     * 5 graines (results/opex_join_place_20y_5seeds.json) : 50 OK, dist 50,
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
     * VERDICT DU BANC APPARIE (results/bench_noplan_sitable.json contre results/bench_traction_new.json,
     * 20 graines x 20 ans) : pas d'effet etabli. company_value +4,0 % (t = 0,50, 11/20),
     * performance_history +1,9 % (t = 0,85), vehicules -1,1 %. Sous le plancher de detection.
     * Le minimum recule (1,79 M -> 1,18 M) et le CV passe de 0,28 a 0,34. La graine 42 seule
     * recule de 28 %.
     *
     * ⚠️ DEFAUT PASSE A 1 LE 2026-09-09 (decision utilisateur), sur deux arguments :
     *   1. Le banc n'a jamais montre de BAISSE : moyenne POSITIVE (+4,0 %) et non significative.
     *      Ce qui bloquait etait la dispersion (minimum, CV) et la graine 42 seule -- or une
     *      graine ne tranche rien (docs/taches.md, banc mono-graine insuffisant). Mecaniquement,
     *      le filtre n'ecarte que des sources qui ne peuvent PAS recevoir de gare utile : une
     *      baisse de profit reelle signalerait un faux negatif du predicat, pas un cout du filtre.
     *   2. Le contexte a change : le banc d'aout portait sur 256x256, ou les opcodes n'etaient pas
     *      la contrainte mordante. C46 (carte 1024x1024) a etabli l'inverse sur grande carte --
     *      economiser 23 NOPLAN et leurs ~14 M d'opcodes par SITEA vaut aujourd'hui bien plus.
     *
     * A/B APPARIE SUR LE CODE ACTUEL (2026-09-09, 5 graines x 3 ans, apres l'indexation spatiale
     * et la refonte des candidats -- le verdict d'aout portait sur une version anterieure) :
     * valeur +1,1 % (ON gagne 4/5 graines), profit/an -0,7 %, score -1,8 %. AUCUNE baisse de
     * profit : pas de signal de faux negatif du predicat.
     * ⚠️ MAIS le VOLUME baisse : vehicules -7,7 %, gares -5,7 %. Or le volume est precisement
     * l'ecart n°1 identifie contre AAAHogEx (~85 % de l'ecart de profit vient de 8x moins de
     * vehicules et de gares, docs/taches.md en tete). Le filtre retire donc des lignes qui
     * n'apportaient pas de valeur a 3 ans, mais il pousse dans le mauvais sens sur la metrique
     * que le projet cherche a redresser. A surveiller au banc officiel 20x10 : si la valeur ne
     * compense pas la perte de volume a 10 ans, revenir a 0.
     * 5 graines x 3 ans est un diagnostic, PAS le banc officiel (20 graines x 10 ans apparie).
     * 0 reste le bras historique EXACT du classement, conserve pour l'A/B. */
    AddSetting({
      name = "origin_sitable",
      description = "Drop rail candidates whose source has no land tile seeing the cargo: 1 = enabled (default since 2026-09-09), 0 = historical ranking",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Partage de bassin sur une gare jointe. Defaut 0 DEPUIS LE 2026-08-29, apres banc apparie.
     *
     * CE QUE 1 FAIT. Quand une extremite du candidat reutilise un StationID deja a nous, la
     * production de CETTE extremite est divisee par (lignes rail deja sur ce StationID pour ce
     * cargo + 1). Le dest fret n'est PAS divise. Inerte si station_join = 0.
     *
     * VERDICT (results/bench_basin_share.json, paire results/bench_basin_share_paired.json, 20 graines
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
     * VERDICT DU BANC APPARIE (results/bench_v2_road.json, 20 graines x 20 ans, OpexAI contre
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
     * (results/bench_v2_road.json, pre-traction). SUR L'ARBRE COURANT ce n'est plus vrai
     * (results/bench_road_8675309.json) : 2 368 267 contre 2 282 217 a road_mode=0, emprunt 0,
     * months_of_bankruptcy 0. Les deux bras sont identiques au 1er janvier 1971. Campagne
     * 20 ans : 0 tentative routiere -- le continue-not-break de la traction laisse le rail
     * prendre le cash residual, le break cash de la route ne s'exerce plus. Pas de garde-fou
     * a ecrire. Re-baseline 2026-08-30 : `results/bench_road_current.json`, 20 graines × 20 ans,
`road_mode=1` contre `road_mode=0` avec traction et `road_pax_catchment_pct=86` :
performance_history +70,35 (+15,3 %), t = 5,65, 18/20 ; company_value +13,5 %, t = 2,24.
Le mode route est donc reconfirme sur l arbre courant.
     *
     * SITEA/B (2026-08-30). OpexRoadSites saute les tuiles non constructibles : 48 sondes
     * etaient brulees sur des maisons/industries qui ont du cargo. 5 graines : SITE
     * 14/18 -> 0, OK 2 -> 6 (results/opex_road_sitable_20y_5seeds.json).
     *
     * TRACEX (2026-08-30). 32 L (contre 12) et facade vers l'autre bout. nLong=0.
     * 5 graines : TRACEX 5->2, OK 6->8, pax 2->4 (results/opex_road_tracex_20y_5seeds.json). */
    AddSetting({
      name = "road_mode",
      description = "Build short road lines (bus town-town, and truck freight industry-industry / industry-town): 1 = enabled, 0 = rail-only baseline",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Hypothese C40 : les bus directs ville-a-ville peuvent cannibaliser le bassin des
     * aeroports. 0 conserve fret et rabattement, et ne touche ni l'aerien ni les lignes deja
     * ouvertes ; il ne retire que la famille OpexRoadPaxCandidates du vivier des nouveaux
     * projets. Le defaut 0 privilegie le profit des aeroports ; 1 reconstitue le bras bus du
     * banc apparie. */
    AddSetting({
      name = "road_pax_build",
      description = "Build new town-to-town passenger bus lines: 0 = disabled by default to preserve airport demand, 1 = enabled; freight and hub feeders stay enabled",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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

    /* Decision utilisateur : la reserve ne doit jamais depasser UN mois d'entretien, contre 3 mois
     * (quarterlyBuffer) dans la branche dynamique et un forfait fixe dans la branche statique. Ce
     * plafond passe sous CASH_RESERVE_MIN des que l'entretien annuel tombe sous 60 000 £, et sous 0
     * si la flotte est vide -- assume, pas un bug : le plafond prime sur le plancher. */
    /* Marges de tresorerie exigees EN PLUS de la reserve sur le chemin aerien (decision
     * utilisateur du 2026-09-03). Le diagnostic 1v1 montre 88 refus insufficient_cash pour 3
     * acceptations : la marge, jusqu'a 30 000 £, pese un ordre de grandeur de plus que la reserve
     * (~7 000 £). Reglage SEPARE de reserve_maint_cap pour que le banc puisse attribuer. */
    /* C13 (remarque de grok, 2026-09-02 ; motive par le banc du 2026-09-03). Le sac a dos
     * maximisait la somme des revenus, jamais du profit -- d'ou le resultat contre-intuitif
     * "plus de capital fait construire moins" : un objectif de revenu depense le budget
     * supplementaire en projets plus gros, donc moins nombreux. */
    AddSetting({
      name = "knapsack_roi",
      description = "Legacy knapsack maximises annual PROFIT and branches on profit density (default). 0 = legacy revenue objective, for comparison only.",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* docs/taches.md S0 undecies nonies (2026-09-03) : mesure directe du vivier -- l'aerien y
     * occupe 43 % des 128 places (56 en moyenne) pour 0 selection par le sac a dos en 16 ans,
     * parce qu'il coute ~131 000 £ contre un capitalBudget moyen de 40 000 £, et que le vivier est
     * rempli sur budgetScore (une densite) sans jamais tester la financabilite.
     *
     * ADOPTE le 2026-09-03 par decision utilisateur, MALGRE un banc d'isolation NEUTRE (20 graines
     * x 3 ans, results/bench_pool_financeable_iso_3y_20seeds.json) : company_value +8,1 % (t=1,48,
     * NS), profit_year +11,7 % (t=1,52, NS), aucune moyenne ne franchit le plancher de detection.
     * Le test des signes isole deux effets reels sous ce plancher : profit du dernier trimestre
     * gagne (16/20, p=0,012) mais median_station_rating perd (5/20, p=0,041). La structure ne
     * casse rien ; elle n'a simplement pas encore prouve de gain de valeur mesurable. */
    AddSetting({
      name = "pool_financeable",
      description = "Filter pool admission on the highest ever-observed mobilisable capital before truncating to PROJECT_POOL_K, instead of ranking by density alone: 1 = enabled (default, adopted 2026-09-03 despite a neutral isolation bench), 0 = rank by density alone",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* P1 : repli empirique rail-only temporaire. L'artefact source du ×1,7
     * n'est plus dans l'arbre ; P1.1 doit le remplacer par le devis physique
     * avant élection. Les autres modes ne sont pas multiplies. */
    AddSetting({
      name = "capital_calibration",
      description = "Use mode-specific physical capital calibration for affordability (rail 170%; default). 0 = historical model-cost control",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_prequote",
      description = "P1.1 experimental control: quote the best eligible rail candidates before affordability selection; rejected at -30.7% value in paired 5x6 and disabled by default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_prequote_keep_plan",
      description = "P1.3: reuse a prequoted rail plan only after a full AITestMode revalidation at build time; 0 = discard it historically",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* P1.2 : sonde de terrain en lecture seule, aucune decision. Marche le trajet quasi-direct
     * candidate.src -> candidate.dst avant tout pathfinding, compte les tuiles complexes (pente,
     * eau, cote) et les segments complexes, journalise P1_2_TERRAIN pour correler hors-ligne avec
     * le devis P1_1_QUOTE sur les memes candidats. N'existe que sous rail_prequote=1. */
    AddSetting({
      name = "rail_terrain_probe",
      description = "P1.2 read-only probe: cheap straight-line terrain scan (slope/water) logged alongside P1.1's real quote for offline correlation; 0 = inactive (default), no live decision impact",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* P4 (docs/taches.md, added 2026-09-08 solely to isolate P4 in the P1xP3xP4 factorial
     * without duplicating a Git tree): gates OpexBuildFailureIsAbandonable's exclusion of
     * transient cash refusals (CASH / ERR_NOT_ENOUGH_CASH) from the abandon memory.
     * 0 reproduces the pre-P4 behaviour where any build failure is memorised as durable. */
    AddSetting({
      name = "abandon_memory_transient_guard",
      description = "P4: exclude transient cash refusals (CASH / ERR_NOT_ENOUGH_CASH) from the abandon memory; 1 = enabled (default), 0 = historical (any failure is durable)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* docs/taches.md S3 undecies (2026-09-03), diagnostic results/diag_airserved_probe.json.
     * OpexBuildAirRoute calcule les StationID puis rend les TUILES (`builder_air.nut:831-832` puis
     * `:898-899`). main.nut lit bien ces champs comme des tuiles ; le code de hub, non. La garde
     * `alreadyConnected` comparait donc un StationID a une tuile et etait structurellement
     * toujours fausse : NEUF liaisons aeriennes sur la MEME paire de villes en 3 ans (graine 42),
     * huit d'entre elles au prix d'un avion seul. Le meme defaut rendait `maxRoutes` inoperant et
     * annulait la decote de saturation `/(routes+1)`.
     * ⚠️ Ce correctif RETIRE une source de croissance qui, mesuree par avion, payait souvent bien
     * (ROI 105 % et 147 % sur deux des doublons) : il doit etre chiffre au banc, pas suppose bon. */
    AddSetting({
      name = "air_hub_fix",
      description = "Resolve air line airport tiles to station IDs in hub discovery and the already-connected guard: 1 = fixed (default), 0 = pre-2026-09-03 behaviour that allowed unlimited duplicate routes on one town pair",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Sonde A6 : calcul et journal du vecteur, sans effet sur le classement ni la construction. */
    AddSetting({
      name = "tension_probe",
      description = "Log the four-resource tension vector for ranked projects: 1 = measurement only, 0 = no calculation (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Plafond de croissance derive du flux mensuel reel, instrument separe du plan. */
    AddSetting({
      name = "air_demand_cap",
      description = "Cap growth of each air fleet from captured monthly town production and aircraft throughput: 1 = enabled, 0 = physical airport cap only (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* Dimensionnement du plan par le meme flux, independant du plafond de croissance. */
    AddSetting({
      name = "air_demand_plan",
      description = "Size new air plans from captured monthly town production instead of population and fixed fleet caps: 1 = enabled, 0 = historical planning model (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_margin_v2",
      description = "Lower the air cash margins (refleet 2000->0, two new airports 30000->15000, one 12000->6000): 1 = enabled, 0 = current margins (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "reserve_maint_cap",
      description = "Cap the cash reserve at one month of fleet maintenance, overriding the floor: 1 = enabled, 0 = no cap (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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

    /* Ordre de chargement passagers aerien : 1 = OF_FULL_LOAD_ANY (attente plein chargement aux deux aeroports),
     * 0 = OF_NONE (chargement partiel et depart immediat, defaut). */
    AddSetting({
      name = "air_full_load",
      description = "Air passenger load order: 1 = full load any, 0 = no full load (fast partial departure, default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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

    /* Part de la production totale d une ville qu un arret de bus capte, en pourcentage.
     *
     * 86 est adopte apres le banc apparie 20 graines (results/bench_road_pax_catchment.json) :
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

    /* Nombre maximal de maisons couvertes par un arret de bus au rayon 3.
     *
     * C23 / modelisation physique du bassin de captage pax routier. Un arret a un rayon de
     * 3 tuiles (zone de 7x7 = 49 tuiles). Compte tenu de la voirie et des espaces libres,
     * il couvre physiquement au maximum ~20 maisons. La part de captage de la ville est donc
     * min(road_pax_catchment_pct, (20 * 100) / houses).
     * Dans un village de 35 maisons -> 57 % de captage.
     * Dans une aglomeration de 250 maisons -> 8 % de captage. */
    AddSetting({
      name = "road_stop_catchment_houses",
      description = "Maximum houses covered by a radius-3 bus stop (physical catchment bound, default 10)",
      min_value = 1, max_value = 100,
      easy_value = 10, medium_value = 10, hard_value = 10,
      custom_value = 10,
      flags = 0
    });

    /* D4 : Delai moyen d'arret et de chargement/dechargement a la station pour les bus passagers */
    AddSetting({
      name = "road_pax_dwell_days",
      description = "Average station dwell and loading time for passenger road vehicles in days (default 6)",
      min_value = 0, max_value = 20,
      easy_value = 6, medium_value = 6, hard_value = 6,
      custom_value = 6,
      flags = 0
    });

    /* D4 par mode : l'aerien passagers realise un revenu median 1,0427 fois
     * celui predit (diag_road_purpose, 10 ans x 5 graines). 104 corrige ce
     * biais sans modifier route, rail ou fret ; 100 reconstitue le controle. */
    AddSetting({
      name = "air_pax_revenue_calibration_pct",
      description = "Air passenger revenue calibration percent: 104 = measured default; 100 = uncalibrated control",
      min_value = 1, max_value = 200,
      easy_value = 104, medium_value = 104, hard_value = 104,
      custom_value = 104,
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
     * VERDICT (results/opex_refleet_20y_4seeds.json, graine 42, 20 ans) : COAL 15 passe 2->1
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
    /* Correctifs de flotte. Revue flotte et entretien, docs/taches.md S0 nonies -- deux defauts
     * qui visent tous le meme symptome mesure : 3,26 vehicules par gare contre 2,71 chez
     * AAAHogEx, et 8x moins de gares.
     *
     * ⚠️ CORRIGE (2026-09-08) : cette liste comptait un 3e point sous 0 (« rail_refleet est
     * INJOIGNABLE »), affirmant que son bloc vivait derriere un return anticipe commande par
     * rail_expand, atteignable seulement sous fleet_fix=1. C'etait deja faux au moment de
     * l'ecrire : le commit 3a15646 (« fix items G1 G7 from code review », 2026-09-07 11:10) a
     * rendu cette garde INCONDITIONNELLE dans _expandRailLines et dans la tache "expand"
     * (commentaire G6§1, main.nut) -- rail_refleet est reellement atteignable au defaut livre
     * (rail_expand=0, rail_refleet=1), independamment de fleet_fix. docs/taches.md repetait la
     * meme erreur (proposait de retirer rail_refleet comme code mort) ; corrige le meme jour.
     *
     * 0 (defaut, comportement historique) :
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
     * ADOPTE AU BANC LE 2026-09-02 (results/bench_isolation_3y_20seeds.json, 20 graines x 3 ans,
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
     * Groupes, ils ont ete mesures NUISIBLES le 2026-09-02 (results/bench_pricing_3y_20seeds.json,
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
      description = "Legacy setting, ignored: rail bands now come from catalog.bounds (epoch kinematics). Kept so existing benches still load.",
      min_value = 5, max_value = 40,
      easy_value = 25, medium_value = 25, hard_value = 25,
      custom_value = 25,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "staged_bootstrap",
      description = "Cascade pax par distance: air seul, air+rail, rail seul, route seule; fret au premier tour. 1 = actif (defaut), 0 = monolithique",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
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
      name = "air_site_cache",
      description = "Cache airport sites per town and airport type: 1 = enabled (default, C33.1), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_cheap_site",
      description = "C36.3 cheap airport footprint filter (IsBuildableRectangle + water/river/coast + C4) before AITestMode: 1 = enabled (default, adopted 20x10 results/bench_c36_3_cheap_site_10y_20seeds.json: profit +27.4% t=3.68 14/6), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_joined_stops",
      description = "C33.2 : Joined drive-through bus stops placed inside airport construction to expand airport catchment into the town (AAAHogEx piece stations): 1 = enabled (default, adopted), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_pax_overlap",
      description = "Pax road: unique catchment after 7x7 overlap, hub-town feeders skipped if they sit in the airport catchment, boardings capped by headway accumulation. 1 = enabled (default), 0 = historical A+B",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_pax_voirie",
      description = "Passenger bus stops on existing roads (drive-through); depot stays off-road. 1 = enabled (default), 0 = cul-de-sac on clear tiles",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_cheap_trace",
      description = "C37 cheap L-corridor probe (2 sites, 2 L) for pax dist<=12 including feeders: use that plan or CHEAPX (banned). 1 = enabled, 0 = historical (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
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
     * POURQUOI IL EXISTE. Banc du 2026-09-02 (results/bench_isolation_3y_20seeds.json, reglage
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
      description = "Portfolio selection on profit per pound of affordable capital, modal choice after the capital test, and regeneration when capital grows (default). 0 = legacy revenue knapsack, for comparison only.",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    /* Nombre maximum de projets construits dans le meme passage du portefeuille. 1 conserve
     * exactement le passage historique : le premier succes regenere le portefeuille et arrete
     * la boucle. Les valeurs superieures ne reutilisent les plans figes qu apres revalidation
     * contre la carte et la tresorerie vivantes (main.nut). La borne 8 est volontairement petite :
     * mesure du 2026-09-02 sur results/diag_vivier_3y.json (5 graines x 3 ans, defauts), le sac a dos
     * finance 203 projets pour 43 construits, mais la MEDIANE des portefeuilles n'en finance qu'UN
     * et le maximum observe est 14.
     *
     * MESURE, ET REGLAGE ECARTE (2026-09-02, results/bench_portfolio_max_batch_3y.json, 20 graines
     * x 3 ans, apparie) : batch 4 contre 1 donne company_value -3,8 % (t = -1,77), profit_year
     * -4,8 %, n_stations -7,9 % (t = -2,04) et n_vehicles -9,5 % (t = -2,94). Test des signes :
     * 11 graines sur 20 sont des NULS EXACTS -- le batch ne se declenche jamais chez elles -- et
     * sur les 9 restantes le batch perd 6 fois contre 3 (p = 0,51 ; p = 0,11 sur le volume).
     *
     * POURQUOI C'EST NUL, verifie aux panneaux (results/diag_batch8_5seeds.json) : un passage REUSSI
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

    /* C38 : ne pas augmenter arbitrairement portfolio_max_batch. Cette option relit le budget
     * et reélit le vivier après chaque succès ; 0 garde exactement le passage unitaire livré. */
    AddSetting({
      name = "portfolio_dynamic_batch",
      description = "C38: rebuild the affordable portfolio after each successful project: 1 = dynamic batch, 0 = historical single-project pass (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* P2 : gardes du batch dynamique. Elles sont sans effet tant que C38 est
     * eteint ; 0 reconstitue l'ancien comportement pour chaque dimension. */
    AddSetting({
      name = "dynamic_batch_reject_limit",
      description = "P2: stop a dynamic batch after this many consecutive rejected attempts; 0 = legacy unlimited scan",
      min_value = 0, max_value = 16,
      easy_value = 3, medium_value = 3, hard_value = 3,
      custom_value = 3,
      flags = 0
    });
    AddSetting({
      name = "dynamic_batch_ops_budget_pct",
      description = "P2: maximum share of the current tick available to a dynamic batch; 0 = legacy 2500-opcode floor only",
      min_value = 0, max_value = 90,
      easy_value = 50, medium_value = 50, hard_value = 50,
      custom_value = 50,
      flags = 0
    });

    /* C36.1 : Caching incremental du vivier post-chantier.
     * Apres une construction reussie, filtre et reelit les candidats deja decouverts en memoire
     * plutot que de relancer OpexBuildProjects de fond en comble (gain : 15 jours -> 0 jour).
     * 1 = actif (defaut, adopte), 0 = regeneration complete historique. */
    AddSetting({
      name = "portfolio_cache",
      description = "Incremental portfolio cache after build (docs/taches.md C36.1): 1 = reuse vivier and reselect (default, adopted), 0 = full rebuild",
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

RegisterAI(OpexAIInfo());
