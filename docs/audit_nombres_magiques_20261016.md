# Inventaire des nombres magiques d'OpexAI — 16 octobre 2026

État audité : `master` à `d80fa01b` (code de `ai/OpexAI/`, OpenTTD 15.3).
Audit **statique en lecture du code**, sans partie OpenTTD, mesure de performance ni
changement de comportement. Les modifications préexistantes dans les documents de
travail n'ont pas été utilisées comme référence pour déclarer un nouveau défaut.

## Lecture du statut

| Code | Signification |
|---|---|
| **A** | Valeur effectivement consultée sur un chemin de décision, de simulation ou de construction avec les réglages par défaut, lorsque le mode concerné se présente. |
| **C** | Code et consommateur présents, mais branche soumise à une option désactivée au défaut, à une condition métier rare, ou à un autre chemin de repli. Le nombre n'agit donc pas systématiquement. |
| **D** | Reliquat démontrable : uniquement déclaration, compatibilité constamment fausse, ou chemin remplacé au défaut. |
| **T** | Constante de protocole ou de conversion (unités, coordonnées, sentinelle, format de sauvegarde) encore utilisée ; sa valeur n'est pas un coefficient économique à optimiser. |

« A » signifie **atteignable dans le code au défaut**, et non « rencontré dans
une campagne réelle ». Une option désactivée peut redevenir effective dans un bras
de banc sans que la branche soit du code mort. Les réglages dans `info.nut` sont
lus par `settings.nut` après leurs initialisations de repli : vérifier la **valeur
`easy_value`**, identique aux quatre profils lorsque mentionnée ici, plutôt que
de déduire le défaut du seul `globals_pre.nut`.

## Inventaire prioritaire : rentabilité et classement

| Valeur(s) | Rôle et impact | Source(s) | Statut et justification |
|---|---|---|---|
| **50 %** `STATION_RATING_PCT` | Prélèvement de l'offre mensuelle dans les modèles ferroviaire et routier ; influe sur nombre de wagons, recette et classement. | `economy.nut:24,226,291,832` | **A** : les estimateurs actifs la lisent. Le code C121 AIR utilise une autre modélisation de note. |
| **130/95/50/25 points**, seuils **7,5/15/30/52,5 jours** | Paliers de note de chargement fondés sur la mécanique OpenTTD, utilisés dans la prévision rail et C121 AIR. | `economy.nut:109-118`, `air_economics_c121.nut:448-468` | **A/T** pour les paliers physiques actuels ; l'ancienne approximation **6,8/13,5/27/47** reste dans `economy.nut:115-118`, **C** sous `ECONOMY_FIX=0` (défaut `economy_fix=1`). |
| **0,036** | Conversion distance ferroviaire/vitesse en jours de trajet ; affecte la capacité et les revenus prévus. | `economy.nut:216,248,272,304,510` | **T/A** : facteur de mécanique, utilisé. Centralisation possible mais ne pas changer le modèle sans mesure. |
| **30 / 30,4 / 365 / 12** | Jours approximés du mois, jours mensuels moyens, jours/an et mois/an ; conversions de flux, vitesse, amortissement. | `economy.nut:87,365,546,859`, `air_economics_c121.nut:444`, `tension.nut:58` | **T/A** : les deux conventions **30** et **30,4** coexistent dans des modèles distincts. Harmoniser constituerait un changement économique à qualifier. |
| **500 pax / 200 fret** | Minimum de profit prédit par millier d'itérations pour admettre un candidat rail. | `candidates.nut:26,776-785` | **A** : `VIVIER_RATIO_FILTER` est alimenté par `policy_portfolio=1`, malgré le commentaire historique évoquant un filtrage différé. Seuils arbitraires déjà testés sans adoption (`docs/rail_magic_filter_p0_20261009.md`). |
| **12/25/45 jours → 130/115/100/60 %** ; multiplicateur **15** | Bonus de rotation et mélange ROI/ratio opcodes dans le score ferroviaire. | `candidates.nut:787-802` | **A** dans le classement local des candidats ; **effet final dépendant** du portefeuille commun, qui choisit ses propres projets. L'audit historique a constaté que le TOP20 local ne déterminait pas seul la décision. |
| **22 %** `TOWN_CATCHMENT_SHARE_PCT` | Part de bassin passagers rail, distincte des 86 % du bus. | `candidates.nut:1651` et ses consommateurs | **A** pour le rail classique ; V207 peut remplacer la part mais son réglage est **0** au défaut. |
| **86 %**, **10 maisons**, **6 jours** | Captage du bus, taille du bassin moyen et séjour en gare routière. | `globals_pre.nut:113-117`, `candidates.nut:2622-2631`, `economy.nut:797-825` | **C/A** : formules et constantes vivantes, mais les nouveaux bus interurbains passagers sont coupés par `road_pax_build=0`; le fret route reste actif. |
| **60 %** `ROAD_SPEED_EFFICIENCY_PCT` | Vitesse commerciale routière dans le devis de durée et de recette. | `economy.nut:747,817` | **A**, dans les projets routiers calculés. |
| **1 000 £/an** `ROAD_MIN_PROFIT_ANNUAL` | Plancher de rentabilité pour garder un candidat route. | `candidates.nut:2465,2519` | **A** pour les candidats effectivement générés. |
| **8** unités d'acceptation | Seuil de pleine acceptation du cargo routier. | `candidates.nut:2473,2888`, `builder_road.nut:186` | **A/T** : convention de l'API de cargo du jeu. |
| **121 % / 100 %** | Coût de financement routier majoré de 21 % par rapport au devis ; `100` utilisé par l'essai P0. | `projects_finance.nut:15-40`, `projects_selection.nut:1162` | **A** : `policy_portfolio=1` active `CAPITAL_CALIBRATION`; majoration route 121. **C** : dérogation `ROAD_FINANCE_UNBIAS_P0=1` OFF par défaut. Le rail prend son réglage **100 %** (`globals_pre.nut:746`, `settings.nut:800`). |
| **64** `PROJECT_TOP_K` ; **20** `TOP_K` ; **48** `ROAD_TOP_K` | Profondeur du portefeuille commun, des candidats rail et du TOP de diagnostic route. | `projects.nut:24`, `candidates.nut:25,2456`, `projects_selection.nut:1654,1930` | **A** pour 64 et 20 ; **A** dans la vue locale route pour 48, qui n'est pas la limite globale d'investissement. Le TOP dynamique est **C**, défaut OFF. |
| **1** `PORTFOLIO_MAX_BATCH` ; plancher relatif **0 %** | Un seul chantier réussi par cycle et filtre relatif au meilleur profit. | `globals_post.nut:64,89`, `projects_selection.nut:1112-1120` | **A** pour batch=1 ; **C** pour le plancher, inactif lorsque `portfolio_floor_pct=0`. |
| **75/25 %** du facteur appris ; pseudo-observation **1** | Lissage de la réalisation projet AIR C121 ; mélange du facteur appris et du prior. | `projects_models.nut:64-112` | **A sous conditions** : `c121_air_project_realization_adaptive=1`; la voie de réalisation directe P0 est aussi configurée à **1**, mais son application attend des observations (`AIR_P0_DIRECT_REALIZATION_ACTIVE`). Ne pas assimiler configuration et effet constaté. |
| **104 %** | Calibrage du tarif passagers aérien de la **voie historique** `OpexAirEconomics`, via `OpexAirFarePerPax`. | `globals_pre.nut:122`, `air_economics_c121.nut:4-17`, `air_route_economics.nut:59,79` | **C** : la chaîne physique C121 est active par défaut et calcule ses tarifs directionnels autrement. Le symbole persiste pour le chemin legacy ; sa valeur configurable ne démontre pas une intervention sur C121. L'essai P0 de réalisation (`docs/air_p0_direct_realization_20261010.md`) est un autre mécanisme. |
| **1,25** | Arbitrage de plans AIR : si l'écart de ROI dépasse 25 %, le ROI prime ; sinon profit absolu. | `air_engine_choice.nut:4-20` | **A** : les deux branches (ancienne et `decisionEconomics`) utilisent le seuil. |
| **1/2 avions**, headway cible **7,5 jours** | Dimensionnement C121 de flotte initiale et cadence de service ; le nombre cible mature est recalculé ensuite. | `air_economics_c121.nut:580-590,1546-1579`, `air_catalog_c121.nut:318-321` | **A** (`c121_air_one_or_two_planes=1`). |
| **175/255**, **8 itérations**, **33 points** ; seuil vitesse **85**, statue **+26** | Initialisation et convergence de la note de gare AIR, bonus d'âge, de vitesse et de statue. | `air_economics_c121.nut:482-528` | **A/T** dans le modèle C121 actif ; à comparer au moteur avant changement. |
| **8 choix identiques / contrôle chaque 32** | Accélérateur du choix d'appareil C121 avec vérification périodique. | `air_economics_c121.nut:1693-1694,1793-1796,2210-2223` | **A** sous `c121_air_game_engine=1` ; bornes techniques de validité du raccourci. |
| **91 jours**, minimum **2** | Fenêtre d'observation du délai des hubs AIR C121. | `globals_pre.nut:708-709`, `air_economics_c121.nut:106-112` | **A/C** selon disponibilité des observations. |
| **365 jours / 30 jours** | Âge de cache des plans/segments AIR ; 30 jours sous branche concurrence visible. | `air_catalog_c121.nut:83,147`, `air_coverage.nut:620-626` | **A** pour 365 au défaut ; **C** pour 30, car `c121_air_visible_competition=0`. |
| **30 000 / 12 000 / 2 000 £** | Réserves de marge de financement selon deux, un ou zéro nouvel aéroport. | `projects_builders.nut:324-334`, `air_engine_choice.nut:791,820,1194,1388`, `air_route_economics.nut:113` | **A** via le devis historique ; le devis physique `air_site_cost_quote=0` et sa marge paramétrée sont **C**. Plusieurs copies numériques sont à factoriser en priorité si l'on refond ce calcul. |
| **1 000 £** | Tampon de solvabilité pour un appareil AIR additionnel, également réintroduit au classement. | `projects_builders.nut:258-269`, `projects_selection.nut:864-877` | **A** sur les projets de flotte correspondants ; couplage à préserver. |
| **13 000 / 2 600 £/an** | A priori du gain propre et coût présumé d'un voisin AIR lors d'un renfort. | `globals_pre.nut:845-846`, `settings.nut:322-324` | **A** sous `v161_fleet_net_marginal=1` (défaut), dans le mécanisme de renfort concerné. Ce sont des paramètres empiriques, non des constantes physiques. |
| **7 jours** `AIR_FLEET_CADENCE_DAYS` | Intervalle de reconsidération de la flotte aérienne. | `globals_pre.nut:831`, `settings.nut` | **A** pour la gestion de flotte AIR selon les lignes construites. |
| **20/16/10/8/5/4 jours** selon type d'aéroport, défaut **12** | Cadence théorique des pistes du **modèle de trajet legacy** utilisé pour le plafond de flotte. | `air_trip.nut:108-118,158-200`, `task_air.nut:1324-1342` | **A** : alors même que C121 chiffre les projets, le contrôleur de flotte utilise encore `OpexAirTripModel` dans `OpexAirCadenceCap`. La coexistence est effective au défaut ; unification = modification économique à mesurer. |
| **30 créations/an, 250 total, 12 par batch ; 4 achats/passage** | Limites de la croissance AIR et du nombre de commandes au même passage. | `task_air.nut:316-334,723-734,1382-1394` | **A/C** : bornes de sécurité réellement utilisées selon la disponibilité de la flotte ; les achats sont resserrés à **1** sous la condition C121 `BelowTarget`. |
| **4 ans**, âge **60/365 jours**, minimum **3 mesures**, profil `balanced90` (**50 j**, **2 vols**, charge **0,40** ou attente **0,50**) | Décision du premier renfort AIR pilotée par les statistiques observées. | `info.nut:784-796`, `task_air.nut:1256-1260`, `probes.nut:365-454` | **A** sous `c121_air_first_live_growth=1`. Les autres seuils `balanced60`, `strict90`, `dual90` dans le même code servent surtout aux comparaisons/logs, **pas** à la décision courante. |
| **30 ans**, **0 %** | Vie amortissable de l'infrastructure et taux d'amortissement effectif. | `economy.nut:46-48,394,583,883` | **A/T** : formule exécutée ; au taux `INFRA_AMORT_PCT=0`, le terme infrastructurel est nul au défaut, sa durée de 30 ans est **sans incidence courante** dans cette formule. |
| **3**, **1 825 jours** | Nombre de bilans déficitaires avant action et âge plafond d'un abandon. | `globals_pre.nut:921`, `lines.nut:298-307` | **A/C** : garde d'exploitation et gestion des paires abandonnées, selon leur type et les événements. |

## Recherche et construction : limites opératoires

| Valeur(s) | Usage | Source(s) | Statut |
|---|---|---|---|
| **160 tuiles** `v168_rail_max_dist` | Borne de génération rail, substituée à la distance tirée de la table d'itérations. | `globals_pre.nut:16`, `candidates.nut:390-396,469-470` | **A**, valeur par défaut qualifiée. |
| **23/33/48/63/81/105/150** et itérations **371/673/2188/4066/7745/15308/53951** | Table empirique V1 « distance → itérations A* », conservée dans les utilitaires. | `candidates.nut:108-143` | **C** pour la borne rail par défaut (V168=160 l'écrase) ; la table est encore appelée avant l'écrasement, donc **pas supprimable sans inspection des consommateurs secondaires**. V2 `365/2342/2652/4123/4516/5977/7825` dépend de `v171_rail_knots=1` (défaut OFF). |
| **10 000 au repli ; 5 000 au défaut réel** `HARD_ITERATION_CAP` | Plafond global de recherche ferroviaire ; budget dynamique réévalué. | `globals_pre.nut:938`, `settings.nut:245-246`, `info.nut:1221-1228`, `builder_rail.nut:101-111` | **A** : le chargement **écrase 10 000 par `pathfinder_hard_cap_k=5 × 1000`**. La description `info.nut:1223` indique encore « 10 = default », commentaire périmé à corriger. |
| **5 000 + 1 000 × lignes** | Budget dynamique de recherche en itérations, plafonné par `HARD_ITERATION_CAP`. | `builder_rail.nut:105-111` | **A** sous `DYNAMIC_PATHFINDER_CAP=true` ; avec le défaut réel à 5 000, ce calcul est immédiatement plafonné à 5 000 : l'incrément par ligne est **sans effet courant**. |
| **50** `PATH_CHUNK` et `RAIL_SEARCH_SLICE` ; **54 020 ticks** | Tranches A* et garde temps (deux ans de jeu) de recherche reprenable. | `builder_rail.nut:30-48`, `task_rail.nut:1428` | **A/T** sur ces chemins. Duplication `const` **imposée par la syntaxe Squirrel** explicitement documentée ; ne pas la « dédupliquer » en expression `const`. |
| **2 000 / 10 000 / 50 000**, largeur **3**, recul **4** | Tailles, budget de récupération et garde de l'A* segmenté. | `builder_rail.nut:62-70,974-1028` | **A/C** lorsque la voie `RAIL_SEGMENTED_SEARCH=true` est effectivement retenue ; le garde 50k est borné par le budget plus petit. |
| **2 000**, facteur **4** | Plancher et majoration du budget d'itérations par tentative. | `builder_rail.nut:76-83` | **A**, heuristique de tentative rail. |
| **200 000** `PATHFINDER_MAX_COST` | Plafond de coût A*, distinct du nombre d'itérations. | `builder_rail.nut:31,635,1028` | **A**, borne technique. |
| **30 / 12 / 4** | Rayon de recherche des quais, nombre maximal de plans et largeur d'assemblage parallèle. | `builder_rail.nut:22-29` | **A/C** selon type de station ; V207 facteur d'échantillonnage **3** OFF sans classement V207. |
| **12 hubs candidats / 25 tuiles / 32 tuiles / 1 500 essais** | Taille du réservoir de sites AIR supplémentaires, rayon de recherche, séparation minimale des villes et budget de sondes. | `builder_air.nut:13-16`, `air_towns.nut:18-29`, `air_planning.nut:1250-1267`, `air_sites.nut:285,462` | **A** lors de la génération d'aéroports C121. |
| **180 000 opcodes / 16 avions** | Enveloppe de tranche du planificateur AIR et plafond d'avions par ligne. | `builder_air.nut:17-21` | **A** dans le planificateur et ses contraintes de flotte. |
| **4..25 tuiles**, `extra_rings=1` | Anneaux de recherche de site et extension C96. | `air_sites.nut:285,462-463`, `globals_pre.nut:470-471` | **A** sur la sélection de site ; sous `c96_air_site_catchment=1`, l'algorithme fait passer la recherche par les sites de catchment. |
| **30 ou 32 tuiles**, vitesse **400** | Distance minimale de la paire AIR en fonction de l'appareil. | `air_planning.nut:2541` | **A** si ce chemin propose une liaison et que l'avion est admissible. |
| **20 tuiles / 2 500 habitants** | Distance minimale d'un bras hub et plafond de population des petites plateformes. | `air_planning.nut:1281,1506,1789` | **A** sur ces familles de plans. |
| **0,414** ; rayon jusqu'à **20** | Approximation octogonale de la distance de vol `max(dx,dy)+0,414×min(dx,dy)` et rayon de demande dans le bassin d'une ville. | `air_coverage.nut:93-100,574-575` | **A** sous C121 ; l'approximation n'est pas une distance euclidienne exacte. |
| **8 unités PASS** ; au plus **4 sites** valides | Critère de captage d'un aéroport et plafond du nombre d'ancres acceptées par C96. | `air_sites.nut:403-409,573`, `globals_pre.nut:470` | **A** avec `c96_air_site_catchment=1`, défaut actif. |
| **800 / 40** | Budget d'amélioration de note municipale à la construction après un refus local. | `air_sites.nut:148`, `air_construction.nut:40,239,372,438` | **C** : chemin réel mais invoqué seulement lorsque les conditions de notation empêchent la pose. |
| **3 lignes par hub** | Plafond appliqué par `air_hub_max_routes`, plus strict que les anciennes valeurs physiques **4/12**. | `info.nut:1882-1889`, `settings.nut:788-790`, `air_towns.nut:185-195` | **A**, défaut 3. Les anciens caps restent du code de repli pour le réglage 0. |
| **30 jours** | Intervalle entre deux tentatives de liquidation d'un chantier AIR interrompu. | `air_recovery.nut:37-39,90-100` | **A** si un ticket de récupération existe. |
| **48 / 16 / 5 / 64 / 4 / 48** | Tracé maximal, rayon des villes/industries, sondes de sites, nombre de sites par extrémité et essais route. | `builder_road.nut:24-29`, usages autour `:600-730` | **A** dans la planification route, conditionnée à un candidat éligible. |
| **12 / 45 / 720 / 8 / 96 / 24 / 12 000 / 50 000 / 4** | Bornes du bassin d'eau, distance minimale, sondes, BFS et marge en capital, nombre de projets. | `builder_water.nut:2-10` | **A/C** pour les projets bateaux générés (`mode_water=1`), moins fréquents ; la cartographie expérimentale C67 reste OFF. |
| **18,5 ticks/jour** | Repli de conversion budget d'opcodes en temps de jeu. | `tension.nut:55-58` | **T/A** si mesure active du débit indisponible. |
| **500 + tranche, min 1 500 ; 2 500 si V88** | Réserve dynamique d'opcodes pour reprendre une recherche rail dans l'ordonnanceur. | `scheduler.nut:426-452,510-526`, `orchestrator.nut:312-324` | **A/C** : 500 et 1 500 sont utilisés dans le chemin de reprise ; la branche 2 500 est **C**, `v88_goods_chain=0`. |
| **2 000 opcodes** | Marge minimale restante pour enchaîner le catalogue AIR incrémental. | `scheduler_tasks.nut:3-12` | **A** sous C121 incrémental, ON au défaut. |
| **150 000 opcodes** | Budget de tranche catalogue AIR. | `scheduler_tasks.nut:284` | **A** sous C121 incrémental ON. |
| **93 000 / 186 000** | Arrondi et dénominateur estimant des jours à partir des opcodes de régénération C76. | `scheduler_tasks.nut:237,519,560`, `orchestrator.nut:1277` | **T/A** dans l'instrumentation/ordonnancement C76 ; nombres recopiés dans plusieurs modules. |
| **2 147 483 647** | Échéance sentinelle pour désarmer une entrée de file. | `scheduler_tasks.nut:94-96,128`, `persist.nut:511,516` | **T/A**. Répété et potentiellement factorisable comme symbole runtime (avec tests Save/Load). |
| **180 jours** | Garde d'âge d'une recherche longue/du stock et attente avant réévaluation. | `orchestrator.nut:300-323`, `task_rail.nut:556,840,2331,2446` | **C/A** selon tâche activée, distinct du deadline de 54 020 ticks. |
| **400 projets** | Plafond de sortie du rapport de candidats, triés avant émission. | `task_report.nut:1228-1249` | **C** : lecture/rapport diagnostique, ne limite pas le vivier principal. |
| **1 000** (×1000), **100** (pourcentage), **256/255** (note), **74/185 ticks**, **16** (unités de longueur rail) | Échelles fixes du ROI et des données OpenTTD, notes cargo, calendrier moteur, encodage longueur. | `projects_models.nut:273-280`, `economy.nut`, `air_coverage.nut:377-380`, `persist.nut:419` | **T** : conventions d'unités et de l'API ; à documenter et nommer si refactor, pas à « calibrer » aveuglément. |

## Valeurs présentes mais sans effet courant ou à effet conditionnel

| Valeur(s) | Pourquoi encore dans le dépôt | Vérification | Statut |
|---|---|---|---|
| **36 lignes / 60 tentatives par an** | Constantes de compatibilité de l'ancien constructeur routier. | `globals_post.nut:10-15` : commentaire explicite ; recherche globale `ROAD_MAX_NEW_LINES_PER_YEAR` et `ROAD_MAX_ATTEMPTS_PER_YEAR` ne trouve aucun consommateur `.nut`. | **D**. |
| `OPEX_ECONOMY_OPCODE_COMPAT_FALSE=false` ; `WATER_OPCODE_COMPAT_FALSE=false` | Tests booléens de compatibilité d'opcodes, parfois des branches vides, gardés pour préserver la forme d'exécution. | `globals_pre.nut:205-221`, `settings.nut:427-429,813-814`, nombreux usages. | **D** pour les chemins `if(flag)` au défaut, bien que les `!flag` soient actifs. Ne pas retirer mécaniquement : cela modifie le budget d'opcodes et potentiellement les décisions. |
| **0 %** `v180_rail_wagon_boost_pct`, **0** délai ; **100/100 %** V212 ; **0/0** V214 | Réglages de variantes ferroviaires récentes conservées pour comparaisons. | `globals_pre.nut:23-25,63-72`, `info.nut`, `economy.nut:226-231,478-486`. | **C** : chemin de réglage existant, correction comportementale OFF ou identité au défaut. |
| **200 % au-delà de 100 tuiles** `V172_*` | Heuristique A* de longue distance. | `globals_pre.nut:97-100`, `settings.nut:128` ; défaut `v172_rail_long_weight_pct=200`. | **A** pour les recherches éligibles ; une expérimentation rejetée peut laisser un réglage actif : l'état du défaut fait foi. |
| **0/0** V177/V182 ; **0 %** V185 ; **0** V192 ; **0** V193/V194/V195 | Minima de distance, filtre fret court, dénominateur, chaîne/variantes de destination. | `globals_pre.nut:17-36`, `settings.nut`, `economy.nut:380-382`, `projects_models.nut:273-274`. | **C**, variantes OFF ou neutres au défaut ; certaines combinaisons sont conditionnées à V88 OFF. |
| **6 villes, 1 000 habitants, bonus 50 %** | Ancienne priorité AIR `early_slot`. | `globals_pre.nut:172-183`; `AIR_EARLY_SLOT` initialisé à `false`. | **C**, seulement si la fonction est réactivée ; `AIR_C83_TARGET_TOWNS=6` est un réglage distinct utilisé sous C83. |
| **650/200 ‰**, minimum **3**, fenêtre **2 ans** | Anciennes classifications d'une réalisation C121 par pression/concurrence. | `globals_pre.nut:559-568`, `projects_models.nut`. | **D/C** : paramètres conservés, mais la branche de classification historique a été retirée ; rechercher toute consommation effective avant suppression individuelle. |
| **1 500/1 000/600/300/100 unités** | Points de note de stock de gare aérienne ; échelons du modèle physique. | `air_economics_c121.nut:471-479` | **A/T**, modèle C121 au défaut, fondé sur les règles de note du jeu. |
| **8 tuiles ; 50 km/h ; 300 ticks ; 260+30 pixels** | Roulement sol/approche/virage et délais techniques des avions. | `air_economics_c121.nut:70-80,197-201,336-342`, `air_trip.nut:19-29` | **A/T** dans C121, **C** dans la voie `air_trip.nut` quand seul le chemin legacy est invoqué. |
| **64 villes** | Fast path synchrone du catalogue AIR sur petite carte. | `scheduler_tasks.nut:37-43` | **C** car le test exige `!C121_CATALOG_INCREMENTAL`, désactivé au défaut. |
| **600 habitants / 100 habitants** | Ancien seuil de ville pour certains aéroports vs nouveau plancher V93. | `air_planning.nut:522,527,1279`, `globals_pre.nut:408-409`, `info.nut` (`v93_airport_no_pop_floor=1`) | **C** pour les tests historiques sous `!V93_AIRPORT_NO_POP_FLOOR` ; **A** pour le filtre V93 réglé à 100, selon le plan. |
| **15 % MAIL**, pondération concurrent **70 %**, plafond **200/100 PASS** | Approximations de la demande dans un ancien estimateur AIR. | `air_town_demand.nut:133-155`, `globals_pre.nut:413-416` | **C** : chemin V93 `v93_air_demand_production=0`, exclu du calcul causal courant C121. De même, l'ancien proxy de population dans `air_planning.nut:844-850` ne pilote pas le classement C121. |
| **730 jours**, **365 jours**, **30 jours / 256 entrées** | Quarantaine V133, TTL de devis de site V126 et cache de concurrence aérienne visible. | `air_towns.nut:422`, `air_economics_c121.nut:122-135`, `air_coverage.nut:420,453` | **C** : branches optionnelles OFF (`v133`, `air_site_cost_quote`, `c121_air_visible_competition`). Distinctes du cache AIR C121 365 jours actif. |
| **6 et 11** (`state`) ; **999 999**, **−999 999 999** ; **1970** | Codes d'état, distances sentinelles, profit minimal sentinelle et année de départ. | `task_projects.nut:601,749-781`, `lines.nut:157`, `economy.nut:952-1016`, `globals_pre.nut:369` | **T/A** tant que les flux associés existent ; préférer des noms d'énumération pour les codes d'état. |
| **0** `c67_terrain_map`, **0** `v88_goods_chain`, **0** `road_pax_build`, **0** `town_growth` | Fonctions encore dans le code, sans activation aux valeurs par défaut. | `info.nut`, `settings.nut`; consommateurs `terrain_map.nut`, `projects_selection.nut`, `candidates.nut`, `task_town.nut`. | **C** : ne pas compter leurs seuils comme contraintes du comportement courant. |

## Risques et entretien suggéré

**Priorité 1 — supprimer les ambiguïtés de statut sans modifier le comportement.**
Documenter que les deux limites routières historiques (36/60) n'ont aucun lecteur ;
séparer les chiffres de configuration des constantes de mécanique OpenTTD et des
valeurs transmises à des diagnostics. Garder les deux tables A* tant que leurs
utilitaires secondaires ne sont pas identifiés précisément. Corriger ensuite le
texte d'aide périmé du plafond A* (`10` annoncé contre `5` chargé), et signaler
explicitement les **deux modèles de temps AIR actifs** : C121 pour les projets,
legacy pour `OpexAirCadenceCap`. Les commentaires « défaut 0 » de certains
raccourcis C121 (`air_economics_c121.nut:1544,1804`) ne correspondent plus
aux valeurs réellement chargées dans `info.nut:2148-2164` : le raccourci
et la fusion concernés sont aujourd'hui activés.

**Priorité 2 — éviter la divergence des chiffres recopiés.** Réserves AIR
`30000/12000/2000`, tampon flotte `1000`, plafond de tâche `2147483647`,
conversion C76 `93000/186000` et seuils de reprise `500/1500` apparaissent
dans plusieurs modules. Une extraction en symbole partagé est envisageable,
mais nécessite des contrats ciblés, car même un refactor qui économise des
opcodes peut modifier les trajectoires de partie.

**Priorité 3 — coefficient économique à examiner seulement dans une campagne
distincte.** Les seuils rail `500/200`, la rotation `130/115/100/60`, le
mixage `×15` et le prior de flotte `13000/2600`
sont des heuristiques pertinentes économiquement. Le calibrage `104 %` ne
concerne que la voie aérienne legacy et ne doit pas être proposé comme
correctif C121 sans preuve d'exposition. L'historique des bancs
`rail_magic_filter_p0_20261009.md` et `air_p0_direct_realization_20261010.md`
interdit d'en déduire un gain en les retirant. Cet inventaire ne modifie
aucun défaut et ne requalifie aucun échec.

## Annexe reproductible : littéraux du code

`docs/archives/nombres_magiques_occurrences_20261016.csv` contient les
occurrences extraites du **code** Squirrel de `ai/OpexAI/**/*.nut` : chemin,
ligne, valeur, `definition`/`inline`, source. Le lexeur d'inventaire masque
les commentaires `/* */`, `//` et chaînes avant l'extraction, puis ignore
les littéraux ordinaires `0`, `1`, `2`, `0.0`, `1.0`, `2.0`.

Résultat : **72 fichiers `.nut` examinés, 2 024 occurrences non triviales dans
67 fichiers**, dont **205 en définitions** et **1 819 en expressions**.
Les **189** occurrences dans `info.nut` décrivent principalement les bornes et
défauts des réglages et ne sont pas toutes des nombres magiques de décision.
Le CSV est une **couverture lexicale**, pas un graphe d'appels : il inclut des
conversions exactes, des indices, des codes de sonde et des seuils dans des
branches OFF. Les tableaux précédents apportent le classement sémantique des
familles prioritaires ; ils ne prétendent pas que chacune des 2 024 occurrences
a été validée dynamiquement.

Vérifications : comparaison des valeurs `easy_value` de `info.nut` avec
`settings.nut`, recherches de consommateurs `rg`, lecture des appels concernés,
et recherche des duplications. Aucun Docker, benchmark ni test économique
exécuté pour cet audit documentaire.
