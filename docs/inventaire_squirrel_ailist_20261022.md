# OPCODE-AILIST-1 — inventaire statique des parcours Squirrel

> **Archive datée du 22/10/2026.** Cette photographie provient du code local à cette date, avec des modifications non commitées. Les occurrences, numéros de ligne et priorités ne reflètent pas nécessairement `origin/master` aujourd'hui. Aucune optimisation proposée ici n'est qualifiée ni adoptée.

**22 octobre 2026 — étape 1/5, inventaire seul, sans changement de `.nut` ni partie OpenTTD.**

## Périmètre et interprétation

L'analyse porte sur tous les `.nut` appartenant à `ai/OpexAI/`, y compris les modules propres `pathfinder_v90/`, et exclut `ai/library/` et `.worktrees/`. Elle part des sources **locales au moment de cette lecture**, qui comprennent des modifications non validées dans l'arbre de travail. La recherche lexicale qui masque chaînes et commentaires (`python -X utf8 sweeps/inventory_squirrel_loops.py --summary`) repère **1 584 boucles** `for`/`foreach`/`while` dans **82 fichiers avec boucles** parmi **88 `.nut` lus**. Une boucle de contrôle d'ordonnanceur, de sérialisation, d'A* ou de pose de rails n'est pas forcément un parcours remplaçable par `AIList`. Réciproquement, un scan de tableau dans un helper peut cacher un filtre important.

**A** : opération de liste directement disponible en natif, sans substituer une décision métier. **B** : prévaluation réellement exécutée dans l'API NoAI, avec une fonction de l'API passée directement à `Valuate`. **C** : seule une *partie* du filtrage devient native ; une passe bornée en Squirrel conserve états, candidats ou actions. **D** : transformation `AIList` inadéquate, avec le motif indiqué. Les sites « déjà natifs » ne sont pas un gisement à compter à nouveau. Une ligne peut être C globalement et comporter un sous-filtre B : le classement s'applique à **la boucle et son effet observable**, pas à une instruction isolée.

Le coût est **non mesuré à la granularité de chaque boucle**, sauf mention expresse. `~25–100 × N` opcodes Squirrel pour une passe simple et `~50–200 × N` pour une passe avec tests/API sont seulement des **ordres de grandeur de tri**, non des mesures, ni une économie promise : appels API, conversions `AddItem`, allocations et suspensions changent les constantes. Pour un produit cartésien, remplacer `N` par le nombre de paires effectivement visitées. Priorité théorique `fréquence × nombre d'éléments × coût par élément` ; aucun classement numérique fin n'est possible sans profil par site.

Notation des tailles : `T` nombre de villes, `I` nombre d'industries, `P` producteurs d'un cargo, `Q` accepteurs, `S` sites AIR, `H` hubs, `L` lignes possédées, `V` véhicules, `E` moteurs, `R` rayon local en tuiles, `K` taille du top-K. Sur **256² = 65 536** tuiles et **1024² = 1 048 576** tuiles, un scan complet comporte exactement ces deux volumes ; un rectangle local comporte `w×h`, un anneau `O(R)`, un ensemble de paires jusqu'à `T(T−1)/2` ou `P×Q`. Les tailles `T`, `I`, `S`, `L`, `V`, `E` **dépendent de la génération et de la partie** : elles ne valent pas 16 fois plus sur 1024² par définition. *Exemple de sensibilité uniquement* : à densité constante, `T=100` sur 256² et `T=1600` sur 1024² impliqueraient respectivement 4 950 et 1 279 200 paires, mais ces nombres ne sont **pas** des observations du jeu. Dans les tableaux, `T/T`, `I/I` signifie que le modèle de taille est le même sur les deux cartes et que les valeurs réelles sont à mesurer.

Fréquences : **passe** = génération/republication ou re-sélection ; **tranche** = reprise d'un worker (souvent plusieurs fois par mois/tick) ; **événement** = mise à jour ciblée ; **construction** = exécution après choix ; **sonde** = branche de mesure conditionnelle. « par tick » n'est employé que si le chemin est réellement appelé par l'ordonnanceur à cette cadence. L'absence de sonde du site est écrite `n.m.`.

## Priorités de revue, par gain potentiel décroissant

Chaque cellule « sites » donne les **départs exacts** des boucles ; plusieurs boucles d'une même famille partagent un contrat d'optimisation. `ops` décrit le **coût existant** lorsque la source permet de l'attribuer, sinon une estimation *du travail Squirrel*, jamais un gain garanti.

| Priorité / classe | Occurrences (`ai/OpexAI/`) et fonction | Travail et cardinalité 256² / 1024² | Cadence ; coût en opcodes | Préfiltrage natif proposé, limite décisive |
|---|---|---|---|---|
| **P0 C** | `candidates.nut:1714,1737,1778` — `OpexRoadFreightCandidates`; miroir reprenable `po01c_generators.nut:307,333,376` — `OpexPO01CRoadFreightCandidates` | Producteur→industrie `P×Q`, producteur→ville `P×T` (deux cartes : `P×Q/P×Q`, `P×T/P×T`) ; filtres de service, distance, acceptation | Passage fret complet ou tranche PO-01 ; **n.m.** par boucle, estimation `O(P(Q+T))×50–200` + coût `OpexMakeRoadCandidate`; compteurs `freightIndustryOps`, `freightTownAcceptanceOps` disponibles si activés | **B en amont** : `AIIndustryList_CargoAccepting(c)`, `Valuate(AIIndustry.GetDistanceManhattanToTile, source.tile)`, `KeepBetweenValue` ; **C global** : villes via liste de *tuiles* et `AITile.GetCargoAcceptance`, puis réconcilier ordre, service, abandons et statistiques |
| **P0 C** | `candidates.nut:1203,1209,1217,1224,1275` — génération RAIL fret ; `po01c_generators.nut:148,156,208` — `OpexPO01CFreightCandidates` | Source `P`, puits `Q` ou villes `T`, jusqu'à `P×(Q+T)` / idem paramétrique | Génération RAIL fret et tranches PO-01 ; **n.m.** par paire, estimation `O(P(Q+T))×50–200` + évaluation économique | Préselection native cargo/puits + Manhattan, `KeepBetweenValue` ; **C** : contrôle des lignes, contrats V179/V264, production et `OpexMakeCandidate` gardent l'ordre d'une boucle reprenable |
| **P0 C** | `candidates.nut:1037,1049,1062,1064` — génération PAX rail ; `po01c_generators.nut:31,44,58,61` — `OpexPO01CPaxCandidates` | Production `T`; grille de voisins et paires, jusqu'à `T(T−1)/2` sur les deux cartes, mais **grille locale** réduit souvent le nombre | Une passe/tranche par campagne PAX ; compteurs `paxPreparationOps`, `paxPairsScanned`, coût par couple **n.m.** ; estimation `50–200×voisins` hors évaluation | `AITownList` + `Valuate(AITown.GetLastMonthProduction,cargo)` pour préproduction ; distance native par source *si* liste de tuiles ; **C** : grille, deux sens, exclusion des lignes et scoring multisources restent Squirrel ; conserver V276 |
| **P0 C** | `candidates_v276.nut:264,279-300` — `OpexV276Enumerate`; `candidates_v276.nut:268` — tri natif **existant** | Paires par tranche, borne `V276_EVAL_CAP=500` évaluées/unité ; espace `T²` ou `P×Q`, sur les deux cartes | Worker par tick **avec budget et curseur** ; filtre `O(voisins)` n.m., tri déjà natif | Tester des sous-listes natives **par source et par bande** ; la boucle générale reste **D** pour son curseur, son contrôle `GetOpsTillSuspend` et son `AddItem(a*n+b, score)` ; ne pas la remplacer par un `Valuate` massif sans checkpoint |
| **P1 C** | `air_planning.nut:584,587` — `OpexAirPlansNewPairs`; `air_planning.nut:1257` — `OpexAirPlansHubToSite`; `air_planning.nut:1416-1417` — `OpexAirPlansHubToHub` | `S(S−1)/2`, `H×S`, `H(H−1)/2` / mêmes formules à chaque taille | Par passe AIR, déjà découpée via curseurs/quotas ; n.m. par paire ; l'audit du 12/10 attribuait 65–78 % du budget 1970–71 au **scan AIR global**, pas à chacune de ces boucles | **C** : distance/filtre d'admission natifs sur petits lots si un gisement persiste ; **D** pour l'énumération complète, reprises, construction des plans, `break` et cache V278 lazy |
| **P1 C** | `projects_selection.nut:748,796,865` — `OpexProjectSelectAffordable`; `projects_selection.nut:987,1032` — `OpexProjectInsertDefensive` | `N_projets`, insertion `N×log K` (bisection) ou `N×K` fallback ; même expression sur deux cartes | Chaque sélection/re-sélection ; `select.full`, `pub.select.score.insert` mesurables, pas par occurrence | Possible **C** pour seuil de profit ou de capital **si scores déjà matérialisés en valeurs entières** ; **D** pour classement C77/early-slot et égalités revenue/score, `OpexProjectFitFleetToBudget` et états vivants. Ne pas prétendre qu'un `Sort` API ordonne des objets Squirrel avec tuple complexe |
| **P1 C** | `candidates.nut:880-892` — `OpexTopK`, appelé notamment après générations ; `air_towns.nut:7,9,277,285`, `builder_water.nut:21,23,472` — insertions triées | `N×K` où `K` est petit ; Squirrel `array.insert` et `while`, `N` variable / idem | À chaque candidat admissible ou plan ; le span V154 a déjà montré **2,1 k → 0,44 k opcodes par insertion**, soit **−4 à −8 M/an** en 1972–74 pour la modification déjà livrée ; ce n'est pas le gain potentiel du présent lot | **C/D** : un `AIList` indexé avec valeurs pré-calculées pourrait trier puis `KeepTop`, mais score flottant, ordre stable des ex æquo, deuxième critère et récupération des objets ne sont pas équivalents sans preuve ; forte probabilité de travail déjà optimisé |
| **P1 C** | `builder_rail.nut:6295,6296,6336,6341` — recherche de stops V207 | Rectangle `w×h` local, shortlist de candidats puis exclusion spatiale `maxStops` ; même dimensions locales sur deux cartes | À la construction d'une gare rail ; **n.m.**, estimation `50–200×w×h` + essais constructeur ; un `Valuate` sur tout le carré peut augmenter les opcodes si arrêt précoce | `AITileList_Rectangle`, `Valuate(AITile.GetClosestTown/ AIRoad.IsRoadTile / AITile.GetCargoProduction)`, `KeepValue`, `KeepAboveValue`, `Sort` natifs ; maintenir tri production-desc puis distance-asc, écartements et `AITestMode` en Squirrel |
| **P1 C** | `air_coverage.nut:449,465-473` — `OpexC121StationCompetitionBuckets` | `N_gares × couverture locale`, aire totale limitée au catchment ; sur deux cartes taille locale identique à densité comparable | Par endpoint B9 si branche active ; **n.m.** ; coûteux potentiellement par tuile | `AIStationList(...).Valuate(AIStation.HasCargoRating,cargo)` puis `KeepValue(1)` ; `GetCargoRating` dans une liste séparée ; intersection avec tuiles couvertes. **C** : sommes/maxima par tuile et cache de couverture restent métier |
| **P1 C** | `air_coverage.nut:230-327`, `air_construction.nut:57-130` — choix des stops routiers des endpoints AIR | Zone locale (couverture) et petite shortlist / idem | Par endpoint / construction ; **n.m.** ; coût surtout production et essais | Préfiltrage de tuiles **déjà natif** à `air_coverage.nut:264-280` ; conserver classement production/distance et actions, limiter les scans redondants |
| **P2 C** | `air_sites.nut:580-582`, `air_sites.nut:268,271,406,410` — anneaux de site | `O(R²)` pour tous rayons, `O(R)` par anneau ; taille locale indépendante de 256²/1024² sauf bord | Par recherche de site AIR, avec premier succès et budget ; **n.m.** | `AITileList` anneau natif avec filtres `IsWaterTile`, `IsCoastTile`, `GetClosestTown`, `AIAirport.GetNearestTown` et `Sort` **déjà implémenté** dans `OpexAirFindSiteRing`, `air_sites.nut:199-246`. Reprendre ce modèle seulement si la variante historique est réellement exécutée |
| **P2 C** | `builder_water.nut:143,144,145` — `OpexWaterFindSite` ; `builder_water.nut:396,397` — paires docks dans `OpexWaterPlans`; miroirs `po01c_generators.nut:499,501` | Carré `(2×couverture+1)²` local ; docks `S_w(S_w−1)/2` / idem | Par passe eau ; `dock_test_ops`, `bfs_ops`, `pair_filter_rank_ops` séparés sous profil ; coûts par boucle **n.m.** | `AITileList_Rectangle` + `Valuate(AITile.IsCoastTile).KeepValue(1)` au préfiltrage **C** ; BFS de connectivité, quotas et sélection de site **D**. Le `while` BFS (eau) reste indispensable |
| **P2 C** | `builder_rail.nut:677,684,685` — `OpexV307StationPlans` | Liste native déjà filtrée et triée, puis 8 octants × profondeur ≤12 ; local / idem | Par site de gare ; budget **73 000 opcodes** `OpexOpsClock`, **plafond**, pas mesure de consommation ; `OpexV307SiteTry` | `AITileList_IndustryProducing/Accepting`, `Valuate(GetSlope/IsBuildable/DistanceManhattan)`, `Sort` **déjà natifs** en `:664-674`. **C** seulement si filtre distance ≤`2R` fait avant bucket ; octants, diversité et arrêt budgétaire restent D |
| **P2 B/C** | `task_v250.nut:188,193,217` — `OpexV250TargetedOrder` / `OpexV250RunTest` | 2–3 parcours `AITownList`, taille `T/T` ; taille change selon densité | Sous V250 conditionnel, par tentative de droits ; **n.m.**, ~`50–200×T` Squirrel | `towns.Valuate(AITown.GetPopulation); towns.Sort(SORT_BY_VALUE, ...)` pour le quantile de population (**B**), `Valuate(AITown.GetAllowedNoise); KeepValue(0)` pour la première classe ; **C** sur rivaux, propriété et classement stable |
| **P2 C** | `catalog.nut:412,428,619,668,728,785,835,847,944,983` — rafraîchissement types/cargos/moteurs | `E` ou `N_cargos`, indépendant géométriquement de taille carte, dépend des NewGRF | Régénération catalogue/événement ; **n.m.** par filtre | Plusieurs `Valuate(AIEngine.IsBuildable)` et `KeepValue` **déjà actifs**. Préfiltrer `CanRefitCargo`, `IsWagon` ou types compatibles via **fonctions API directes**, puis décision de meilleur moteur en Squirrel (vitesse, capacité, coût, tie) |
| **P2 C** | `air_towns.nut:175,197` — `OpexAirOwnSlotTownCounts`/`OpexAirV134SaturatedHubState`; `projects_selection.nut:147,174` — `OpexEarlySlotSelectionState`/`OpexDefensiveSlotSelectionState` | `N_gares_air`; ne dépend pas directement de surface | Par recalcul de demande/selection ; **n.m.**, ~`50–200×N_gares` | Pré-`Valuate(AIStation.GetNearestTown)`, `KeepValue`, voire population sur une liste de villes, mais C83 utilise la ville *physique du slot* `OpexAirSlotTownId`, l'unicité par ville, et mutations de table : **C**, attention stations partagées |
| **P2 C** | `lines.nut:99,111` — `OpexLineVehicleIds` | Véhicules desservant une gare, sous-ensemble de `V`; idem | Événements/ferraillage ; **n.m.**, plutôt petites listes | `AIVehicleList_Station`, `Valuate(AIVehicle.GetVehicleType)`, `KeepValue`, `Valuate(AIVehicle.GetCapacity, cargo)`, `KeepAboveValue(0)` ; **C** : filtrage sur les *ordres vers l'autre gare* et propriété de la ligne indispensable (incident historique de ferraillage partagé) |
| **P2 C** | `lines.nut:129,132,138,149,159,173` — `OpexFindLineForVehicle`; `air_planning.nut:864,881`, `task_report.nut:219,683,885` | `L` lignes × quelques véhicules ou stations, `L/L` | Événement ou rapport périodique ; **n.m.**, jusqu'à `O(L×V_ligne)` | Un index Squirrel `vehicle→line` ou `station→lines` pourrait réduire la recherche ; **C côté structure de données, D côté AIList** : les objets de lignes et ordre des replis ne sont pas des éléments API ; aucune fonction native ne donne la ligne historique Opex |
| **P2 C** | `task_v250.nut:125,133`, `air_towns.nut:572-614` — tuiles de station/ville/ennemis | Fenêtres rectangulaires locales ; indépendant du nombre total de tuiles | Sondes V250 / garde de site, conditionnels ; **n.m.** | `AITileList_Rectangle` + `Valuate(AITile.IsStationTile)` et `KeepValue(1)` ; une partie existe dans `air_towns.nut:598-599` ; le contrôle propriétaire/slot unique reste Squirrel |
| **P2 A** | `probe_v307.nut:408` — boucle « meilleur type rail » | `N_types_rail`, très petit et indépendant carte | Sonde V307 ; **n.m.** | `types.Sort(AIList.SORT_BY_ITEM, AIList.SORT_DESCENDING); local chosen=types.Begin()` ; simple max **A**, mais priorité de gain faible et sonde opt-in |
| **P3 C** | `air_economics_c121.nut:1710-1765,1877-1930` — filtrage/tri d'avions ; `air_engine_choice.nut` | `E_air`, indépendant taille de carte | Choix moteur, ponctuel / par projet ; **n.m.** | Filtrer par `AIEngine.CanRefitCargo` et caractéristiques API (**B partiel**), garder en Squirrel les scores dérivés, la stabilité et tie par ID ; **C** |
| **P3 D** | `projects_update.nut:16,18,91,93,173,175,330,331,489,493,538,541,576` ; `orchestrator.nut:915,917,925`; `po01c_regen.nut:303,305,311` — regroupements/insertions | Groupes de projets et lots, `N_projets`, changent avec vivier ; idem | Publication/événement/regen, potentiellement répétée ; **n.m.** | Tables de projets à payload, fusion par clés, déduplication, conservation des positions et repères : **D** pour un remplacement AIList pur ; il faut vérifier les caches V277/V279 et la neutralité de l'ordre avant toute refonte |
| **P3 D** | `scheduler.nut:197,208`, `orchestrator.nut:538`, `po01c_regen.nut:30,41,54,60,404` — rotation des tâches et coroutines | File `N_tâches`, petits ou segments reprenables ; idem | Par tick/tranche, budget d'opcodes explicite ; **n.m.** | Ordonnanceur, `yield/resume`, sentinelles et curseurs ; **D** sans équivalent AIList et risque de famine si atomicité modifiée |
| **P3 D** | `builder_water.nut:216,260`, `pathfinder_v90/aystar.nut` et `builder_rail.nut` (boucles A*, voies, signaux et rollback) | Nombre de nœuds/frontières de chemin : variable ; jusqu'aux bornes algorithmiques, pas 65k/1M automatiquement | Par chemin/construction, très coûteux dans son ensemble ; **n.m.** par boucle, coûts A* de l'architecture distincts | Exploration avec voisinage, coûts cumulés, état visité, files/heap, actions et suspension ; **D** pour AIList, même si certains filtres statiques de tuiles en entrée peuvent être **C** |

### Appels Squirrel implicites : les 19 `array.sort()`

Ces appels effectuent un parcours/tri **sans boucle écrite** et ne figurent donc pas dans les 1 584 lignes de l'index. La recherche `--sort-calls` les localise exhaustivement ; aucun `.filter()`/`.map()`/`.reduce()` de tableau n'est présent. Les six `.find()` rencontrés dans `air_towns.nut:368-373` portent sur **des chaînes d'erreur**, hors cible. Les coûts par site ne sont pas mesurés : comparer un `array.sort()` sans closure à la construction plus le tri d'une `AIList`, car la version avec comparateur est susceptible d'appeler Squirrel plusieurs fois par comparaison (`O(N log N)`). `B` signifie qu'une projection API directe peut remplacer la préparation et le tri ; `C` exige la restitution de l'ordre métier ; `D` signifie que le comparateur métier n'est pas un valuateur natif.

| Site exact, fonction | Tri effectué ; taille 256² / 1024² | Cadence ; coût et classe | Équivalent proposé / limite |
|---|---|---|---|
| `air_towns.nut:567` `OpexTownPopulationTopQuartileThreshold` | Quantile de populations, `T/T` | Seuil AIR selon appel ; `O(T log T)` n.m. ; **B** | `AITownList.Valuate(AITown.GetPopulation)`, `Sort` natif, isoler le rang/valeur ; conserver l'arrondi du 75e centile |
| `task_v250.nut:189` `OpexV250TargetedOrder` | Même quartile, `T/T` | V250 conditionnel ; `O(T log T)` n.m. ; **B** | Même projection native ; attention cas liste vide |
| `air_coverage.nut:291` `OpexAirB9PredictJoinedStops` | Production desc., distance asc., `N_tuiles_bassin` / idem local | Endpoint AIR B9 ; `O(N log N)` n.m. ; **C** | `AIList` clé `tile→production` + `Sort` desc. réduit le travail du premier critère ; préserver 2e critère et stabilité |
| `air_construction.nut:99` `OpexAirBuildJoinedStops` | Même tuple production/distance, `N_tuiles_bassin` / idem local | Construction endpoint ; `O(N log N)` n.m. ; **C** | Idem, essais physiques et premier succès demeurent Squirrel |
| `builder_rail.nut:535` `OpexV207RankStationPlans` | `unionValue` décroissant, `N_plans` / idem local | Planification quai ; `O(N log N)` n.m. ; **C** | `AIList.AddItem(planIndex, unionValue)` + `Sort(SORT_BY_VALUE,DESC)` ; contrôler le premier plan en cas d'égalité |
| `builder_rail.nut:6326` `OpexV207RailBuildJoinedStops` | Production desc., distance asc., `N_tuiles_zone` / idem local | Construction stop ; `O(N log N)` n.m. ; **C** | Projection par valeur en liste native + départage exact restant Squirrel |
| `builder_road.nut:475` `OpexRoadPlanPaxVoirie` | Distance croissante, paires `S_road²` / idem | Planification réseau ; `O(N log N)` n.m. ; **C** | `AIList` index de paire → distance, `Sort` ASC ; vérifier ordre égal |
| `candidates.nut:65` `OpexFreightCargoOrder` | Revenu cargo desc., ID cargo asc. ; `N_cargos` / idem | Par passe fret ; `O(N log N)` n.m. ; **C** | `AICargoList.Valuate(AICargo.GetCargoIncome,20,0)` + tri ; préserver départage par ID |
| `rail_long_window_probe.nut:10` `OpexRLW03TopTownCohort` | Population desc., ID ville asc. ; `T/T` | Sonde RLW03 ; `O(T log T)` n.m. ; **C** | `AITownList.Valuate(AITown.GetPopulation)` + `Sort/KeepTop` ; tie ID obligatoire |
| `task_report.nut:1112` `OpexAI::_reportC78Candidates` | Classement des candidats au-delà de 400, `N_vivier/N_vivier` | Rapport C78 conditionnel ; `O(N log N)` n.m. ; **C** | `AIList` index→profit et `KeepTop(400)` seulement si critères secondaires/tie intégralement conservés |
| `task_report.nut:1561` `OpexAI::_v292TryBuildHq` | Distance croissante, `N_sites_HQ` / idem local | Construction HQ conditionnelle ; `O(N log N)` n.m. ; **C** | `AIList` index→distance, `Sort` ASC ; conserver ordre ex æquo et boucle d'action |
| `air_economics_c121.nut:1736` `OpexC121ScanRoutePlaneEngines` | `upperScore` desc. + ID avion asc. ; `E_air/E_air` | Choix moteur C121 ; `O(E log E)` n.m. ; **D** | Score calculé en Squirrel et départage multi-clés : pas de `Valuate(API.method)` équivalent |
| `air_economics_c121.nut:1900` `OpexC121ChooseRoutePlane` | Idem `upperScore`, `E_air/E_air` | Choix avion par route ; `O(E log E)` n.m. ; **D** | Même motif, parcours petit et strict |
| `air_planning.nut:217` `OpexAirPlansPrepare` | Comparateur C121 de priorité villes, `T/T` ou shortlist | Préparation passe AIR ; `O(T log T)` n.m. ; **D** | Score/comparateur métier et état de site ; un `Valuate` closure Squirrel ne résout rien |
| `opcode_exact.nut:522` `OpexAirFleetSortPrecomputed` | Rendement de lignes AIR, `L_air/L_air` | Sonde opcodes ; `O(L log L)` n.m. ; **D** | Rendement calculé hors API, conserver comparateur et même ordre |
| `opcode_exact.nut:585` `OpexAirJoinedCandidatesExact` | Comparaison spécialisée de candidates, `N_sites/N_sites` | Sonde opcodes ; `O(N log N)` n.m. ; **D** | Critères de correspondance/ordre de référence de la sonde |
| `task_v249.nut:80` `OpexV249GetPendingV252Cost` | Âge desc., profit asc., rang asc., `N_tickets` / idem | Maintenance V249 ; `O(N log N)` n.m. ; **D** | Tuple de trois critères non natifs, ordre affectant la réparation |
| `task_v252.nut:71` `OpexAI::_dispatchV252AirEngineRefresh` | Même tuple âge/profit/rang, `N_tickets` / idem | Maintenance V252 ; `O(N log N)` n.m. ; **D** | Même départage métier, priorités d'action |
| `task_v259.nut:190` `OpexAI::_v259PrepareBridgeQueue` | Priorité des ponts calculée par `OpexV259CompareBridges`, `N_ponts` / idem | Réparation V259 ; `O(N log N)` n.m. ; **D** | File de chantier, comparateur et chronologie à préserver |

Pour les candidats **C** dont la clé native est un score entier unique, le motif de code est :

```squirrel
local ranked = AIList();
for (local i = 0; i < source.len(); i++) ranked.AddItem(i, source[i].score);
ranked.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
// Relire source[index] en respectant EXACTEMENT l'ordre des égalités historique.
```

Cette proposition n'affirme aucun bénéfice tant que les conversions `AddItem` et le départage n'ont pas été mesurés. Le `array.sort()` sans comparateur peut déjà être efficace : ne pas le remplacer uniquement parce qu'il est écrit en Squirrel.

**Bilan chiffré de préclassement, boucles + appels de tri :** **1 603 sites** = **A 1**, **B 3**, **C 264**, **D 1 127**, **H 208 hors cible**. Décomposition : les **1 584 boucles** sont réparties en A 1 / B 1 / C 255 / D 1 119 / H 208 dans l'index, auxquels s'ajoutent **19 tris** B 2 / C 9 / D 8. Ces chiffres indiquent la **couverture d'inventaire** ; le tri automatisé classe les boucles D par prudence et ne constitue pas 1 127 preuves indépendantes d'impossibilité. Les gains devraient être qualifiés au niveau des familles du tableau priorisé ; les 1 603 sites ne sont ni autant de changements souhaitables ni autant de postes indépendants de coût.

### Extraits natifs proposés (schémas, à adapter et tester en étape 2)

**Fret industrie→industrie (B en amont, C pour la décision) :**

```squirrel
// Une source/cargo par tranche, jamais tous les produits cartesiens d'un coup.
local sinks = AIIndustryList_CargoAccepting(cargo);
sinks.RemoveItem(sourceIndustryId);
sinks.Valuate(AIIndustry.GetDistanceManhattanToTile, sourceTile); // fonction API
sinks.KeepBetweenValue(minDistance, maxDistance); // bornes INCLUSIVES
for (local id = sinks.Begin(); !sinks.IsEnd(); id = sinks.Next()) {
  // Ici seulement : l'ordre historique, desserte, abandons, financement,
  // OpexMakeCandidate / OpexMakeRoadCandidate, statistiques, checkpoints.
}
```

**Tuiles/acceptation cargo (B en amont, C au choix) :**

```squirrel
local tiles = AITileList();
// Ajouter seulement les tuiles centre des villes retenues (pas toute la carte).
foreach (town in shortlistTowns) tiles.AddItem(town.tile, 0);
tiles.Valuate(AITile.GetCargoAcceptance, cargo, 1, 1, coverage);
tiles.KeepAboveValue(ROAD_ACCEPTANCE_FULL_UNIT - 1);
// Rejoindre tile -> town et garder les tests de service/distance dans l'ordre.
```

**Fenêtre de tuiles locale (B au filtrage, C au constructeur) :**

```squirrel
local area = AITileList();
area.AddRectangle(topLeft, bottomRight);
area.Valuate(AIRoad.IsRoadTile); area.KeepValue(1);
area.Valuate(AIRoad.IsRoadStationTile); area.KeepValue(0);
area.Valuate(AIRoad.IsRoadDepotTile); area.KeepValue(0);
area.Valuate(AITile.IsStationTile); area.KeepValue(0);
area.Valuate(AITile.GetCargoProduction, paxCargo, 1, 1, rayonBus);
area.KeepAboveValue(0);
// Essais AITestMode, distances à la plateforme et non-chevauchement après.
```

**Quantile de population sur AITownList (B) :**

```squirrel
local towns = AITownList();
towns.Valuate(AITown.GetPopulation);
towns.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
local position = (towns.Count() * 3) / 4;
// L'API n'offre pas d'acces aleatoire indexé : iterer jusqu'au rang voulu
// ou isoler le rang via KeepBottom(position+1), puis lire la dernière valeur.
```

**Comptage de listes déjà natives (A) :** utiliser `stations.Count()`, `vehicles.Count()` et, pour un min/max d'une valeur API, `Valuate(API.Method, args...)` + `Sort` + `GetValue(Begin())` si la liste est **non vide**. Pour un `AIList` ayant des valeurs déjà calculées, `KeepAboveValue`, `KeepBelowValue`, `KeepBetweenValue`, `KeepValue`, `RemoveList`, `KeepList`, `KeepTop`, `KeepBottom` évitent une boucle Squirrel ; conserver le coût de création ou de conversion dans la comparaison.

### Garde-fous indispensables à l'étape suivante

1. `Valuate` est **atomique, non suspendable**. Sur 1024², **1 048 576 tuiles** ne sont jamais un lot acceptable par défaut ; borner à un rectangle, une source, une cargaison ou une tranche. La création d'une `AITileList_Rectangle` ne garantit pas que la valuation du rectangle passe dans le budget.
2. `Valuate` avec une **closure/function Squirrel** re-paie le coût Squirrel pour chaque élément ; cela **n'est pas** le « valuateur natif » B. Une fonction API dont la signature ne prend pas directement la clé de liste (ex. ville→tuile puis `GetCargoAcceptance`) réclame une conversion préalable et un nouveau comptage complet des coûts.
3. `KeepBetweenValue` inclut les deux bornes : les comparaisons d'origine `<`, `<=`, `>` doivent être traduites exactement ; attention aux valeurs négatives et à `KeepAboveValue` / `KeepBelowValue` dont la stricte inégalité change les égaux.
4. `AIList.Sort`/`KeepTop` ne reproduisent pas forcément l'ordre d'un tableau Squirrel stable, la priorité C77, les ex æquo sur `revenueAnnual`, les clés de tie ou un score flottant. `Sort` natif lui-même est atomique. Tracer les **identités** et positions, pas seulement le nombre de candidats.
5. Ne pas réintroduire une liste du monde entier au détriment des index et caches existants (`V276`, `V277`, `V278`, `V279`, `C41.20`) ; préserver les checkpoints `yield`, Save/Load, quotas, sondes de rejet et la sortie anticipée après action. Pour les listes de véhicules de stations partagées, conserver absolument le filtre sur les deux extrémités de la ligne.
6. Sous sélection et scans AIR, les chemins à défaut **diffèrent suivant la taille de carte** : V276 et V278 sont automatiques sur grandes cartes seulement (réglages `settings.nut`/`info.nut`). Comparer le coût et la sortie du chemin réellement actif à 256² et à 1024² séparément.

## Mesures historiques utilisables comme contexte, pas comme gains de boucle

* `docs/taches.md` (V277/V279, 20/10) : sur **256²** avec span probe graine 42 × 1 an, postes `catalog.rebuild` **10,81→0,72 M**, `pub.filter` **6,25→0 M**, `pub.select.filter` **4,55→2,84 M**, sélection **61,7 k→54,3 k par appel** ; **−11,8 M/an** sur les postes visés de cette optimisation *déjà existante*. Recompter le même delta serait double compter. La campagne 20×10 du couple présentait une tendance économique défavorable, sans adoption automatique.
* `docs/taches.md` (V154/V157, 12/10) : insertion d'un candidat **2,1 k→0,44 k opcodes**, gain environ **4–8 M/an** aux années citées ; résultat historique relatif à une autre optimisation, et non gain garanti pour `AIList`.
* `docs/taches.md` (RLW-03) : une sonde mensuelle déclenchée ON a consommé **63 815 / 98 200 opcodes** en pointe ; l'effet total de la sonde n'est pas imputable à une boucle unique.
* `docs/taches.md` (C80/PO-01) : certaines régénérations réactives complètes ont consommé **5–12 M opcodes par événement**. C'est le coût du pipeline complet, pas la somme supposée remplaçable par listes natives.
* `docs/taches.md` (V278 sur **1024²**, ligne 443) : coût de sites AIR **9,64 M → 0,44 M opcodes/an** et **8 sondages au lieu de 253** ; optimisation lazy déjà disponible, aucun gain « AIList » à recompter. Le V277 AIR, ligne 432, rapporte **10,93 M → 0,78 M** sur la publication concernée ; effet antérieur, indépendant du présent inventaire.
* `docs/taches.md` (V296c, ligne 241) : contre-exemple **48,7 k → 488,5 k opcodes par appel**, environ **×10**, lorsque le préfiltre natif évaluait tout le carré de quais et perdait la sortie anticipée. Le nombre de tuiles prévaluées est un facteur de coût à contrôler avant toute conversion C.
* `docs/taches.md` (C67, ligne 1666) : `terrain_valuate.nut` lit des blocs **5×5 en 2 982 → 1 454 opcodes (−51 %) et 10×10 en 12 395 → 3 885 (−68 %)** face au lecteur de référence, tests déjà archivés ; appels `Valuate` atomiques maximaux observés **141/516 opcodes** et blocs **1 733/4 283**. **Ce lecteur n'a pas de consommateur de décision actif au défaut**, donc **gain actuel de production nul**. Les boucles d'agrégation (somme des hauteurs) y restent Squirrel faute d'opération somme native.
* Mesures disponibles **dans le code** : `profile.paxPreparationOps`, `freightIndustryOps`, `freightTownAcceptanceOps`, `bfs_ops`, `pair_filter_rank_ops`, `OpexSpanAgg("pub.select.score.insert")`, `terrain_valuate.nut` détaille le coût des opérations natives `Valuate` et `Sort`. Cette lecture n'a exécuté aucune de ces sondes : **aucune moyenne nouvelle n'est attribuée** à ces boucles.

## Lots de remplacement proposés après cette étape

| Lot | Sites prioritaires | Condition de départ | Risque de divergence |
|---|---|---|---|
| **L1 — fret producteurs→puits** | `candidates.nut`, `po01c_generators.nut` (RAIL/ROAD), V276 sous-lots par source | Statistiques nombre de producteurs, `Q` avant/après, tuiles parcourues et opcodes par cargo à 256² puis 1024² ; préserver `stats.*` | Moyen : l'ordre d'énumération, V179/V264, la cible événementielle et `V276_EVAL_CAP` peuvent changer le top-K |
| **L2 — sites locaux route/rail** | `builder_rail.nut:6295-6315`, `air_coverage.nut` endpoints, `builder_water.nut` | Prouver que la shortlist était parcourue intégralement avant le changement ; mesurer `N` du rectangle et taux de rejet | Élevé si la sortie anticipée gagne actuellement davantage qu'une valuation atomique |
| **L3 — petits scans natifs isolés** | `task_v250.nut:188`, `probe_v307.nut:408`, éventuellement stations `air_towns` | Tests de parité des ex æquo/rangs et des identités à la même date | Faible à moyen ; gain en opcodes modeste |
| **L4 — filtres de préselection AIR et moteurs** | `air_coverage.nut:449`, `catalog.nut` et `air_economics_c121.nut` | Vérifier activation réelle et cache existant, mesurer liste initiale/réduite | Moyen : score métier/dépendance NewGRF et données non invariantes |
| **L5 — structures candidates et classements** | `projects_selection.nut`, `candidates.nut:880-892`, `projects_update.nut` | Seulement si L1–L4 insuffisants et si la fidélité ordre/ties est prouvée sur sorties complètes | Très élevé : cas C77, early-slot, trésorerie et classement multidimensionnel |

Chaque lot devra ensuite (étape 2+) mesurer ses **propres opcodes et nombre d'éléments visités** sur mêmes graines/conditions, contrôler les décisions et la neutralité selon `AGENTS.md` §4. Aucun banc, smoke ni adoption n'appartient à la présente étape 1.

## Index de contrôle des occurrences

La localisation ci-dessous est générée automatiquement à partir du même état de source. Elle sert à vérifier que les 1 584 boucles, notamment les parcours **D** et les petites boucles hors domaine, n'ont pas disparu de l'audit. Les classes des lignes de priorité ci-dessus sont **revues sur le code** ; l'index est un contrôle lexical avec un classement conservateur, **pas une preuve que chaque boucle classée D est optimale**. Les raisons D suivent les familles : algorithme à état/cumulative, action exécutée par élément, parcours d'objets Squirrel, tranches/suspension ou séquences dont l'ordre détermine la sortie. Les boucles de contrôle et les itérations sur constantes sans liste métier restent **H (hors cible AIList)** et ne participent pas au compte des remplacements. Le relevé des fonctions utilise une approximation syntaxique qui ignore commentaires et chaînes ; les lignes renvoient toujours au fichier source.

<!-- INDEX_BEGIN -->

### Totaux de repérage

Ce **premier tri lexical** compte les occurrences, pas les fonctions ni les lots ; C/D dans l'index sont **conservateurs et révisables** lors de la revue de chaque famille. Les classes de la table priorisée, documentées avec contexte métier, prévalent.

| A | B | C | D | H (hors cible) | Total parcouru |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 255 | 1119 | 208 | 1584 |

Pour chaque ligne : volume et cadence sont des **modèles**, pas des observations de partie ; coût individuel **n.m.** sauf mention du tableau principal. Estimation exploratoire pour C : `~25–200 × N` opcodes de boucle et tests Squirrel hors API et calcul métier ; D et H : gain AIList présumé nul, à revalider avant modification. Les fragments natifs applicables sont ceux du tableau et des extraits ci-dessus.

#### `ai/OpexAI/air_c83_repair.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 8 | `OpexC83RepairSnapshot` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 10 | `OpexC83RepairSnapshot` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 25 | `OpexC83RepairSnapshot` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 57 | `OpexC83RepairFindSites` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/air_catalog_c121.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 16 | `OpexC121CatalogRefreshStationLines` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 26 | `OpexC121CatalogRefreshStationLines` | D | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 35 | `OpexC121CatalogRefreshStationLines` | D | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 64 | `OpexC121CatalogRankDirtyTowns` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 99 | `OpexC121CatalogClearPlanSnapshot` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 232 | `OpexC121MeasureBuiltEconomics` | C | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 233 | `OpexC121MeasureBuiltEconomics` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_construction.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 112 | `OpexAirBuildJoinedStops` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 116 | `OpexAirBuildJoinedStops` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 126 | `OpexAirBuildJoinedStops` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 410 | `OpexBuildAirRoute` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 437 | `OpexBuildAirRoute` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/air_coverage.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 64 | `OpexAir0310SiteValidityBegin` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 281 | `OpexAirB9PredictJoinedStops` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 300 | `OpexAirB9PredictJoinedStops` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 303 | `OpexAirB9PredictJoinedStops` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 311 | `OpexAirB9PredictJoinedStops` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 358 | `OpexAirB9TownCoverageTiles` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 402 | `OpexC121StationCoverageTiles` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 426 | `OpexC121StationCompetitionBuckets` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 449 | `OpexC121StationCompetitionBuckets` | C | `for` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 465 | `OpexC121StationCompetitionBuckets` | C | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 477 | `OpexC121StationCompetitionBuckets` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 486 | `OpexC121StationCompetitionBuckets` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 504 | `OpexC121StationAllocatedMonthly` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 551 | `OpexAirB9TownUnionMonthly` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 813 | `OpexAirCatchmentProbeEndpoint` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_economics_c121.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 305 | `OpexC121ExistingStationService` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 322 | `OpexC121ExistingStationService` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 470 | `OpexC121RatingTarget` | C | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 635 | `OpexC121AirEconomics` | C | `for` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1617 | `OpexC121GameEngineFindPlane` | C | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1723 | `OpexC121ScanRoutePlaneEngines` | C | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1745 | `OpexC121ScanRoutePlaneEngines` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1887 | `OpexC121ChooseRoutePlane` | C | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1909 | `OpexC121ChooseRoutePlane` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_engine_choice.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 49 | `OpexM3ProbeAirEquipment` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 101 | `OpexM3ProbeAirPreAdmission` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_fleet.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 49 | `OpexAirBestEngineForLine` | C | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 87 | `OpexAirAddPlane` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_flotte1_shadow.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 64 | `OpexAirF1PoolRail` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 65 | `OpexAirF1PoolRail` | C | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 165 | `OpexAirF1Before` | C | `for` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 219 | `OpexAirF1After` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 347 | `OpexAirR1ITTCheckpoint` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 377 | `OpexAirR1ITTObserve` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 399 | `OpexAirR1ITTObserve` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 414 | `OpexAirR1ITTObserve` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 433 | `OpexAirR1ITTObserve` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_lazy_sites.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 12 | `OpexV278CopyContext` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 24 | `OpexV278LinesSignature` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 37 | `OpexV278RestorePrepare` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 65 | `OpexV278HubIndex` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 82 | `OpexV278StorePrepare` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 104 | `OpexV278HeapPush` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 119 | `OpexV278HeapPop` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 142 | `OpexV278LazyState` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 144 | `OpexV278LazyState` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 149 | `OpexV278LazyState` | D | `for` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 195 | `OpexV278ExtendSites` | D | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 240 | `OpexV278LazyPairs` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/air_load7_shadow.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 25 | `OpexAirLoad7IndexStep` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 32 | `OpexAirLoad7IndexStep` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 55 | `OpexAirLoad7Neighbors` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 60 | `OpexAirLoad7Neighbors` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 135 | `OpexAirLoad7Step` | D | `while` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/air_planning.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 140 | `OpexAirPlansPrepare` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 173 | `OpexAirPlansPrepare` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 203 | `OpexAirPlansPrepare` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 212 | `OpexAirPlansPrepare` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 213 | `OpexAirPlansPrepare` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 243 | `OpexAirPlansPrepare` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 340 | `OpexAirPlansFindSites` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 352 | `OpexAirPlansFindSites` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 471 | `OpexAirPlansFindSites` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 572 | `OpexAirPlansNewPairs` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 584 | `OpexAirPlansNewPairs` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 587 | `OpexAirPlansNewPairs` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 811 | `OpexAir0310HubTopologySignature` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 833 | `OpexAir0310CopyHubList` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 848 | `OpexAir0310CopySiteList` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 864 | `OpexAir0310CountStationRoutes` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 881 | `OpexAC04ValidateHubsAtUsage` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 899 | `OpexAir0310RefreshHubRoutes` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 940 | `OpexAir0310RememberPublishedHubPairs` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1008 | `OpexAir0310HubSnapshotStore` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1043 | `OpexAC04ExtraSiteAlreadyKnown` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1076 | `OpexAirPlansDiscoverHubs` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1083 | `OpexAirPlansDiscoverHubs` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1112 | `OpexAirPlansDiscoverHubs` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1131 | `OpexAirPlansDiscoverHubs` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1139 | `OpexAirPlansDiscoverHubs` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1152 | `OpexAirPlansDiscoverHubs` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1164 | `OpexAirPlansDiscoverHubs` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1177 | `OpexAirPlansDiscoverHubs` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1186 | `OpexAirPlansDiscoverHubs` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1203 | `OpexAirPlansDiscoverHubs` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1215 | `OpexAirPlansDiscoverHubs` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1220 | `OpexAirPlansDiscoverHubs` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1257 | `OpexAirPlansHubToSite` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1260 | `OpexAirPlansHubToSite` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1416 | `OpexAirPlansHubToHub` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1417 | `OpexAirPlansHubToHub` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1449 | `OpexAirPlansHubToHub` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1663 | `OpexAirV93NextSmallCombo` | D | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1865 | `OpexAirPlans` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_recovery.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 8 | `OpexAirRecoveryOwnsAirport` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 9 | `OpexAirRecoveryOwnsAirport` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 23 | `OpexAirRecoveryBlocksPlan` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 25 | `OpexAirRecoveryBlocksPlan` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 38 | `OpexAirContinueRollback` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 59 | `OpexAirContinueRollback` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 65 | `OpexAirContinueRollback` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 114 | `OpexAirReconcileRollbacks` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 116 | `OpexAirReconcileRollbacks` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 121 | `OpexAirReconcileRollbacks` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 137 | `OpexLoadAirRollbacks` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 145 | `OpexLoadAirRollbacks` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 146 | `OpexLoadAirRollbacks` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/air_route_economics.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 62 | `OpexAirEconomics` | C | `for` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_sites.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 16 | `OpexAirFootprintCheapOk` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 17 | `OpexAirFootprintCheapOk` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 49 | `OpexAirFootprintIsFlat` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 50 | `OpexAirFootprintIsFlat` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 77 | `OpexAirBLevelTerrainSnapshot` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 78 | `OpexAirBLevelTerrainSnapshot` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 268 | `OpexAirFindSiteListed` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 271 | `OpexAirFindSiteListed` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 406 | `OpexAirFindSiteCatchmentListed` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 410 | `OpexAirFindSiteCatchmentListed` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 580 | `OpexAirFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 581 | `OpexAirFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 582 | `OpexAirFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_town_demand.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 7 | `OpexAirDemandPaxCargo` | C | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_towns.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 7 | `OpexAirSortedTowns` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 9 | `OpexAirSortedTowns` | D | `while` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 36 | `OpexAirTownServed` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 60 | `OpexAirTownServed` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 147 | `OpexAirPreemptPickTown` | C | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 175 | `OpexAirOwnSlotTownCounts` | C | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 197 | `OpexAirV134SaturatedHubState` | C | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 204 | `OpexAirV134SaturatedHubState` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 251 | `OpexAirTownCentersLinked` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 277 | `OpexAirC83WatchTowns` | C | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 285 | `OpexAirC83WatchTowns` | D | `while` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 291 | `OpexAirC83WatchTowns` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 395 | `OpexV133CountBatchSalvage` | C | `for` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 537 | `OpexV133SaveQuarantine` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 549 | `OpexV133LoadQuarantine` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 559 | `OpexTownPopulationTopQuartileThreshold` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 562 | `OpexTownPopulationTopQuartileThreshold` | C | `for` — T villes (256² / 1024²) | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 602 | `OpexTownRivalAirports` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/air_trip.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 85 | `OpexAirLiveRoutesAtAirport` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 89 | `OpexAirLiveRoutesAtAirport` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 125 | `OpexAirBuildRoutesIndex` | C | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 129 | `OpexAirBuildRoutesIndex` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 160 | `OpexAirCadenceCap` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/budget.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 85 | `total` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/builder_rail.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 127 | `OpexRailPlatformCargoValue` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 147 | `OpexV190FindParallelPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 148 | `OpexV190FindParallelPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 156 | `OpexV190FindParallelPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 219 | `OpexV307SinkRoomParallel` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 232 | `OpexV307SinkRoomParallel` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 261 | `OpexV307SinkRoomFilterPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 284 | `OpexV307SinkRoomFilterPlans` | H | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 301 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 304 | `OpexV307SinkRoomIgnoredTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 312 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 313 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 315 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 319 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 324 | `OpexV307SinkRoomIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 334 | `OpexV307SinkRoomPathClear` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 338 | `OpexV307SinkRoomPathClear` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 370 | `OpexV307SinkRoomDemolishExtra` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 432 | `OpexV307SinkRoomPrebuiltPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 437 | `OpexV307SinkRoomPrebuiltPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 453 | `OpexV307SinkRoomPrebuiltReady` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 466 | `OpexV190CollectParallelTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 467 | `OpexV190CollectParallelTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 469 | `OpexV190CollectParallelTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 477 | `OpexV190CollectParallelTiles` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 479 | `OpexV190CollectParallelTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 487 | `OpexV190CollectParallelTiles` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 500 | `OpexV190MergeIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 504 | `OpexV190MergeIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 505 | `OpexV190MergeIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 507 | `OpexV190MergeIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 530 | `OpexV207RankStationPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 542 | `OpexV207RankStationPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 569 | `OpexV307SiteOctantCount` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 584 | `OpexV307SiteTry` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 585 | `OpexV307SiteTry` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 592 | `OpexV307SiteTry` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 677 | `OpexV307StationPlans` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 684 | `OpexV307StationPlans` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 685 | `OpexV307StationPlans` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 695 | `OpexV307StationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 696 | `OpexV307StationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 697 | `OpexV307StationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 739 | `OpexV307SpiralPlanCandidates` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 740 | `OpexV307SpiralPlanCandidates` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 741 | `OpexV307SpiralPlanCandidates` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 745 | `OpexV307SpiralPlanCandidates` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 746 | `OpexV307SpiralPlanCandidates` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 753 | `OpexV307SpiralPlanCandidates` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 822 | `OpexV307HybridStationPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 834 | `OpexV307HybridStationPlans` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 849 | `OpexV307HybridStationPlans` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 853 | `OpexV307HybridStationPlans` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 899 | `OpexStationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 900 | `OpexStationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 901 | `OpexStationPlans` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 905 | `OpexStationPlans` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 906 | `OpexStationPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 913 | `OpexStationPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 970 | `OpexStationPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1012 | `OpexJoinPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1013 | `OpexJoinPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1015 | `OpexJoinPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1020 | `OpexJoinPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1058 | `OpexV264StationRailBox` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1142 | `OpexV264TrySpreadAnchor` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1148 | `OpexV264TrySpreadAnchor` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1206 | `OpexV264SpreadScan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1212 | `OpexV264SpreadScan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1221 | `OpexV264SpreadScan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1349 | `OpexRailPlatformPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1355 | `OpexRailPlatformPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1385 | `OpexRailPlatformPlans` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1409 | `OpexRailPlatformPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1458 | `OpexIsMountainousMap` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1541 | `OpexCreateRailPathfinder` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1542 | `OpexCreateRailPathfinder` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1613 | `OpexAdvanceRailPathfinder` | D | `while` — L lignes possédées, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1662 | `OpexSegmentTiles` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1668 | `OpexSegmentTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1683 | `OpexCopySegmentTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1693 | `OpexCopySegmentStructures` | H | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1703 | `OpexPlannedStructureKind` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1720 | `OpexCanAppendSegment` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1721 | `OpexCanAppendSegment` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1737 | `OpexSegmentIgnoredTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1746 | `OpexSegmentIgnoredTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1759 | `OpexSegmentPrefixContains` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1776 | `OpexFrontierAlternatives` | D | `while` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1779 | `OpexFrontierAlternatives` | D | `for` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1808 | `OpexDestinationCenter` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1837 | `OpexLocalStructureChoices` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1903 | `OpexV294cGoalDistance` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1913 | `OpexV294cSourceDistance` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1953 | `OpexV294cRetryNoPath` | H | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1989 | `OpexCreateSegmentedSearch` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1990 | `OpexCreateSegmentedSearch` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2059 | `OpexAdvanceSegmentedSearch` | D | `while` — L lignes possédées, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2100 | `OpexAdvanceSegmentedSearch` | D | `while` — L lignes possédées, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2118 | `OpexAdvanceSegmentedSearch` | D | `while` — L lignes possédées, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2146 | `OpexAdvanceSegmentedSearch` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2180 | `OpexAdvanceSegmentedSearch` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2199 | `OpexAdvanceSegmentedSearch` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2204 | `OpexAdvanceSegmentedSearch` | H | `for` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2215 | `OpexAdvanceSegmentedSearch` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2221 | `OpexAdvanceSegmentedSearch` | H | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2225 | `OpexAdvanceSegmentedSearch` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2288 | `OpexPathTiles` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2294 | `OpexPathTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2308 | `OpexV214RouteDistance` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2309 | `OpexV214RouteDistance` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2327 | `OpexV214PathGeometry` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2330 | `OpexV214PathGeometry` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2364 | `OpexMatchPlan` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2375 | `OpexMatchPlanExact` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2420 | `OpexRailPlanContainsTile` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2510 | `OpexJoinPathIsDedicated` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2522 | `OpexPlanHitsSet` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2546 | `OpexTryDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2547 | `OpexTryDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2548 | `OpexTryDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2553 | `OpexTryDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2557 | `OpexTryDoubleTrack` | D | `foreach` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2561 | `OpexTryDoubleTrack` | D | `foreach` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2567 | `OpexTryDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2579 | `OpexTryDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2593 | `OpexTryDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2594 | `OpexTryDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2668 | `OpexV190TraceParallelTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2757 | `OpexV190TraceParallelTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2790 | `OpexV197BuildGuideTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2800 | `OpexV197BuildGuideTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2835 | `OpexV197BuildGuideTiles` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2844 | `OpexV197BuildGuideTiles` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2846 | `OpexV197BuildGuideTiles` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2847 | `OpexV197BuildGuideTiles` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2872 | `OpexV190PlanDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2873 | `OpexV190PlanDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2874 | `OpexV190PlanDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2879 | `OpexV190PlanDoubleTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2885 | `OpexV190PlanDoubleTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2910 | `OpexV190PlanDoubleTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2920 | `OpexV190PlanDoubleTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2935 | `OpexV190PlanDoubleTrack` | D | `for` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2955 | `OpexV190PlanDoubleTrack` | D | `for` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2956 | `OpexV190PlanDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2963 | `OpexV190PlanDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 2966 | `OpexV190PlanDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3003 | `OpexV190PlanDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3049 | `OpexV190PlanDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3094 | `OpexRailCaptureTrackFailure` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3138 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3161 | `OpexV199RetryToBuild` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3163 | `OpexV199RetryToBuild` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 3192 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3199 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3200 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3201 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3215 | `OpexV199RetryToBuild` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3240 | `OpexV199RebuildForHomeward` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3292 | `OpexV199RebuildForHomeward` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3351 | `OpexV296aRunEnd` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3383 | `OpexBuildTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3394 | `OpexBuildTrack` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 3462 | `OpexBuildTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3506 | `OpexBuildTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3521 | `OpexBuildTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3607 | `OpexTestRailTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3649 | `OpexBuildDepot` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3660 | `OpexBuildDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3666 | `OpexBuildDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3713 | `OpexRollback` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3721 | `OpexRollback` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3729 | `OpexRollback` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3736 | `OpexRollback` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3745 | `OpexRollback` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3813 | `OpexBuildTrains` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3853 | `OpexBuildTrains` | D | `for` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3908 | `OpexBuildTrains` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3916 | `OpexBuildTrains` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 3989 | `OpexPlacePathApproachSignal` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4026 | `OpexPlaceJoinSignals` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4154 | `OpexCompleteRailRouteAfterSearch` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4248 | `OpexV131BuildTownClearance` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4249 | `OpexV131BuildTownClearance` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4251 | `OpexV131BuildTownClearance` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4253 | `OpexV131BuildTownClearance` | H | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 4261 | `OpexV131BuildTownClearance` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4263 | `OpexV131BuildTownClearance` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4274 | `OpexV131BuildTownClearance` | D | `foreach` — T villes (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4285 | `OpexV131BuildTownClearance` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4287 | `OpexV131BuildTownClearance` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4297 | `OpexV131BuildTownClearance` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4354 | `OpexSimulateRailInfraCost` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4359 | `OpexSimulateRailInfraCost` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4377 | `OpexSimulateRailInfraCost` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4422 | `OpexSimulateRailInfraCost` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4425 | `OpexSimulateRailInfraCost` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4434 | `OpexSimulateRailInfraCost` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4661 | `OpexExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4665 | `OpexExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4798 | `OpexExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4799 | `OpexExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4838 | `OpexExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4841 | `OpexExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4842 | `OpexExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4849 | `OpexExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4860 | `OpexExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4980 | `OpexV190VerifyPrimaryTrackIntact` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4984 | `OpexV190VerifyPrimaryTrackIntact` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 4994 | `OpexV190VerifyPrimaryTrackIntact` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5011 | `OpexV190VerifyPrimaryTrackIntact` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5039 | `OpexV190RollbackDoubleTrack` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5046 | `OpexV190RollbackDoubleTrack` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5049 | `OpexV190RollbackDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5054 | `OpexV190RollbackDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5059 | `OpexV190RollbackDoubleTrack` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5074 | `OpexV190RollbackDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5082 | `OpexV190RollbackDoubleTrack` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5091 | `OpexV190RollbackDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5106 | `OpexV190RollbackDoubleTrack` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5253 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5257 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5341 | `OpexV190ExecuteRailPlan` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5343 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5348 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5353 | `OpexV190ExecuteRailPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5354 | `OpexV190ExecuteRailPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5398 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5399 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5418 | `OpexV190ExecuteRailPlan` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5423 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5428 | `OpexV190ExecuteRailPlan` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5432 | `OpexV190ExecuteRailPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5433 | `OpexV190ExecuteRailPlan` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5459 | `OpexV190ExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5460 | `OpexV190ExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5530 | `OpexV190ExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5541 | `OpexV190ExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5630 | `OpexPrepareUpgradeSearch` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5631 | `OpexPrepareUpgradeSearch` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5634 | `OpexPrepareUpgradeSearch` | D | `foreach` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5638 | `OpexPrepareUpgradeSearch` | D | `foreach` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5647 | `OpexPrepareUpgradeSearch` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5687 | `OpexExecuteUpgradeAfterSearch` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5707 | `OpexExecuteUpgradeAfterSearch` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5708 | `OpexExecuteUpgradeAfterSearch` | D | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5810 | `OpexTraceTrackTiles` | D | `while` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 5833 | `OpexTraceTrackTiles` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5924 | `OpexV181TryBuildSwitch` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5939 | `OpexV181TryBuildSwitch` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5946 | `OpexV181TryBuildSwitch` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 5951 | `OpexV181TryBuildSwitch` | H | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 6059 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6060 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6071 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6073 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6085 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6088 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6101 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6104 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6159 | `OpexConvertDoubleTrackToLoop` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6181 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6190 | `OpexConvertDoubleTrackToLoop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6201 | `OpexConvertDoubleTrackToLoop` | D | `for` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6206 | `OpexConvertDoubleTrackToLoop` | H | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 6222 | `OpexConvertDoubleTrackToLoop` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6225 | `OpexConvertDoubleTrackToLoop` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6264 | `OpexV207RailBuildJoinedStops` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6295 | `OpexV207RailBuildJoinedStops` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 6296 | `OpexV207RailBuildJoinedStops` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 6336 | `OpexV207RailBuildJoinedStops` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6341 | `OpexV207RailBuildJoinedStops` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 6350 | `OpexV207RailBuildJoinedStops` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/builder_road.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 83 | `OpexRoadAppendSegment` | D | `while` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 89 | `OpexRoadAppendSegment` | D | `while` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 117 | `OpexRoadTraceBuildable` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 166 | `OpexRoadSites` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 197 | `OpexRoadTraceHitsStop` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 233 | `OpexRoadFindDepot` | H | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 241 | `OpexRoadFindDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 243 | `OpexRoadFindDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 264 | `OpexRoadFindDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 355 | `OpexRoadOurBusTiles` | D | `for` — N_gares par compagnie, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 359 | `OpexRoadOurBusTiles` | D | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 367 | `OpexRoadTileTooClose` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 387 | `OpexRoadBfsPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 392 | `OpexRoadBfsPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 404 | `OpexRoadBfsPath` | H | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 427 | `OpexRoadPaxVoirieSites` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 448 | `OpexRoadPlanPaxVoirie` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 467 | `OpexRoadPlanPaxVoirie` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 468 | `OpexRoadPlanPaxVoirie` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 484 | `OpexRoadPlanPaxVoirie` | D | `foreach` — S/H/voisins, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 498 | `OpexRoadPlanPaxVoirie` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 553 | `OpexRoadRollback` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 571 | `OpexRoadRollback` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 589 | `OpexRoadTryJoinStop` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 621 | `OpexRoadTryJoinStop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 632 | `OpexRoadTryJoinStop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 637 | `OpexRoadTryJoinStop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 646 | `OpexRoadTryJoinStop` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 657 | `OpexRoadBuildTrace` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 870 | `OpexBuildRoadRoute` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 886 | `OpexBuildRoadRoute` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 894 | `OpexBuildRoadRoute` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 945 | `OpexRoadRefleet` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 970 | `OpexRoadRefleet` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 996 | `OpexRoadRefleet` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 1003 | `OpexRoadRefleet` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/builder_water.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 21 | `OpexWaterSortedTowns` | D | `foreach` — T villes (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 23 | `OpexWaterSortedTowns` | D | `while` — T villes (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 31 | `OpexWaterTownServed` | D | `foreach` — L lignes possédées, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 46 | `OpexWaterIsNavigable` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 62 | `OpexWaterAdjacentTiles` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 90 | `OpexWaterFindDockAccess` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 98 | `OpexWaterFindDockAccess` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 106 | `OpexWaterFindDockAccess` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 118 | `OpexWaterFindDockAccess` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 143 | `OpexWaterFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 144 | `OpexWaterFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 145 | `OpexWaterFindSite` | C | `for` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 186 | `OpexWaterContains` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 193 | `OpexWaterHasRange` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 213 | `OpexWaterFindConnection` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 216 | `OpexWaterFindConnection` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 222 | `OpexWaterFindConnection` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 243 | `OpexWaterFindDepot` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 244 | `OpexWaterFindDepot` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 256 | `OpexWaterFindDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 260 | `OpexWaterFindDepot` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 264 | `OpexWaterFindDepot` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 294 | `OpexWaterEconomics` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 360 | `OpexWaterPlans` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 372 | `OpexWaterPlans` | D | `foreach` — T villes (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 396 | `OpexWaterPlans` | C | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 397 | `OpexWaterPlans` | C | `for` — S/H/voisins, deux cartes | construction/chemin; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 472 | `OpexWaterPlans` | D | `while` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 487 | `OpexWaterPlans` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 622 | `OpexBuildWaterRoute` | D | `foreach` — N_vivier/K, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/candidates.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 42 | `OpexFreightCargoOrder` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 48 | `OpexFreightCargoOrder` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 71 | `OpexFreightCargoOrder` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 95 | `OpexRailIterations` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 119 | `OpexRailDistanceForIterations` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 182 | `OpexGetEpochVehicle` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 250 | `OpexCargoTransitHorizon` | D | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 281 | `OpexComputeRoadToRailDistance` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 525 | `OpexRailOriginSitable` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 526 | `OpexRailOriginSitable` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 527 | `OpexRailOriginSitable` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 884 | `OpexTopK` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 887 | `OpexTopK` | D | `while` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 921 | `OpexOriginServed` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 940 | `OpexRoadFreightServedIndex` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 943 | `OpexRoadFreightServedIndex` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 946 | `OpexRoadFreightServedIndex` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 950 | `OpexRoadFreightServedIndex` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 967 | `OpexRoadFreightAcceptedTowns` | C | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 981 | `OpexOriginService` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 983 | `OpexOriginService` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1029 | `OpexPaxCandidates` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1037 | `OpexPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1049 | `OpexPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1062 | `OpexPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1064 | `OpexPaxCandidates` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1148 | `OpexV264ConvergentService` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1150 | `OpexV264ConvergentService` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1203 | `OpexFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1209 | `OpexFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1217 | `OpexFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1224 | `OpexFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1275 | `OpexFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1388 | `OpexBuildCandidates` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1472 | `OpexBands` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1473 | `OpexBands` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1616 | `OpexRoadPairServed` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1633 | `OpexTownRoadLineCount` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1650 | `OpexTownBusPaxServed` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1683 | `OpexRoadFreightCandidates` | D | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1688 | `OpexRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1702 | `OpexRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1714 | `OpexRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1720 | `OpexRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1724 | `OpexRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1737 | `OpexRoadFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1772 | `OpexRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1778 | `OpexRoadFreightCandidates` | C | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1880 | `OpexBuildRoadCandidates` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1986 | `OpexBoostTownRating` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1987 | `OpexBoostTownRating` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 2012 | `OpexSubsidyMatchingLineId` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 2070 | `OpexGenerateSubsidyCandidates` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 2154 | `OpexGenerateSubsidyCandidates` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/candidates_v276.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 31 | `OpexV276CargoOrder` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 37 | `OpexV276CargoOrder` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 45 | `OpexV276CargoOrder` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 90 | `OpexV276AddUnits` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 118 | `OpexV276Start` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 122 | `OpexV276Start` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 148 | `OpexV276PrepareUnit` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 149 | `OpexV276PrepareUnit` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 215 | `OpexV276Publish` | C | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 219 | `OpexV276Publish` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 223 | `OpexV276Publish` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 226 | `OpexV276Publish` | C | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 236 | `OpexV276Publish` | C | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 264 | `OpexV276Enumerate` | D | `while` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 323 | `OpexV276Continue` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 369 | `OpexV276Continue` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 393 | `OpexV276Acknowledge` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 398 | `OpexV276Acknowledge` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/capital.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 9 | `OpexCashReserve` | D | `for` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/catalog.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 102 | `OpexRailCruiseSpeed` | D | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 321 | `OpexM3RailLocoChoices` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 328 | `OpexM3RailLocoChoices` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 340 | `OpexM3RailLocoChoices` | H | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 412 | `OpexCatalog::_refreshRail` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 428 | `OpexCatalog::_refreshRail` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 505 | `OpexCatalog::_refreshRail` | D | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 508 | `OpexCatalog::_refreshRail` | D | `while` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 514 | `OpexCatalog::_refreshRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 516 | `OpexCatalog::_refreshRail` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 523 | `OpexCatalog::_refreshRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 535 | `OpexCatalog::_refreshRail` | H | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 574 | `OpexCatalog::_refreshRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 577 | `OpexCatalog::_refreshRail` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 615 | `OpexCatalog::_refreshAir` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 619 | `OpexCatalog::_refreshAir` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 664 | `OpexCatalog::_refreshAir` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 668 | `OpexCatalog::_refreshAir` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 728 | `OpexCatalog::_refreshWater` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 785 | `OpexCatalog::_refreshRoad` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 799 | `OpexCatalog::_refreshRoad` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 802 | `OpexCatalog::_refreshRoad` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 835 | `OpexCatalog::_refreshCargos` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 847 | `OpexCatalog::_refreshTowns` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 861 | `OpexCatalog::_refreshTowns` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 879 | `OpexC121CatalogSeedTownPopulations` | C | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 899 | `OpexC121CatalogTownProductionBatch` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 944 | `OpexCatalog::_refreshIndustries` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 956 | `OpexCatalog::_refreshIndustries` | D | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 967 | `OpexCatalog::_refreshIndustries` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 971 | `OpexCatalog::_refreshIndustries` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 983 | `OpexCatalog::_cargoArray` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1024 | `OpexCatalog::refresh` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1026 | `OpexCatalog::refresh` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1039 | `OpexCatalog::refresh` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/economy.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 361 | `OpexLineEconomics` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 768 | `OpexM3ProbeRailEquipment` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 812 | `OpexM3ProbeRoadEquipment` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/event_handlers.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 46 | `OpexAI::_onVehicleAutoreplaced` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 50 | `OpexAI::_onVehicleAutoreplaced` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 54 | `OpexAI::_onVehicleAutoreplaced` | D | `while` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 71 | `OpexAI::_onVehicleAutoreplaced` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 75 | `OpexAI::_onVehicleAutoreplaced` | D | `while` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 226 | `OpexAI::_onSubsidyAwarded` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 357 | `OpexAI::_onVehicleLost` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 373 | `OpexAI::_onVehicleLost` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/events.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 68 | `OpexAI::_markDirty` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 84 | `OpexAI::_markDirty` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 136 | `OpexAI::_markDirty` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 156 | `OpexAI::_logStalenessRefresh` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 170 | `OpexAI::_logStalenessRefresh` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 179 | `OpexAI::_logStalenessRefresh` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 181 | `OpexAI::_logStalenessRefresh` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 183 | `OpexAI::_logStalenessRefresh` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 196 | `OpexAI::_logStalenessRefresh` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 217 | `OpexAI::_logStalenessRefresh` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 225 | `OpexAI::_logStalenessRefresh` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 330 | `OpexAI::_processEvents` | D | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/goods_v233.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 48 | `OpexV233Support` | D | `for` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 58 | `OpexV233SaveObservations` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 71 | `OpexV233LoadObservations` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 74 | `OpexV233LoadObservations` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 108 | `OpexAI::_v233GoodsStep` | D | `for` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 117 | `OpexAI::_v233GoodsStep` | D | `for` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 186 | `OpexV233SecondaryRivalServed` | D | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 191 | `OpexV233SecondaryRivalServed` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 217 | `OpexV233JoinContextValid` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 229 | `OpexV233FactoryCovered` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 301 | `OpexAI::_v233GraftStep` | D | `for` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 307 | `OpexAI::_v233GraftStep` | D | `while` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 323 | `OpexAI::_v233GraftStep` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 372 | `OpexV233NewPlatform` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 391 | `OpexV233SpendAllowed` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 395 | `OpexV233SpendAllowed` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 401 | `OpexV233SpendAllowed` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 402 | `OpexV233SpendAllowed` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 417 | `OpexAI::_v233PlanStep` | D | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 421 | `OpexAI::_v233PlanStep` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 444 | `OpexAI::_v233PlanStep` | D | `for` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 479 | `OpexAI::_v233Publish` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 480 | `OpexAI::_v233Publish` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 485 | `OpexAI::_v233Publish` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 499 | `OpexAI::_v233Publish` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/ledgers.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 9 | `OpexAI::_logC41MonthlyBusyLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 19 | `OpexAI::_logC41SlackLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 35 | `OpexAI::_recordC41StaleOpportunity` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 59 | `OpexAI::_recordC41StaleOpportunity` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 72 | `OpexAI::_recordC41StaleOpportunity` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 88 | `OpexAI::_logC41AdmissionLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 98 | `OpexAI::_logC41OpportunityLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 160 | `OpexAI::_logC39PassClockLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 232 | `OpexAI::_schedIdlePreDispatch` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 241 | `OpexAI::_schedIdlePreDispatch` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 397 | `OpexAI::_p5ScanCandidatePool` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 399 | `OpexAI::_p5ScanCandidatePool` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 412 | `OpexAI::_p5ScanCandidatePool` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 461 | `OpexAI::_p5ScanCandidatePool` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 478 | `OpexAI::_p5ScanCandidatePool` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 823 | `OpexAI::_schedIdlePostDispatch` | D | `for` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 910 | `OpexAI::_schedIdlePostDispatch` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 933 | `OpexAI::_schedIdlePostDispatch` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 993 | `OpexAI::_schedIdlePostDispatch` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1027 | `OpexAI::_recordC49ScarcityPass` | D | `for` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1077 | `OpexAI::_logC49ScarcityLedger` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1082 | `OpexAI::_logC49ScarcityLedger` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1087 | `OpexAI::_logC49ScarcityLedger` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1145 | `OpexAI::_logC50AnnualReport` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1177 | `OpexAI::_logC50AnnualReport` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1211 | `OpexAI::_logC50AnnualReport` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1353 | `OpexC52EventExposureFields` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1364 | `OpexAI::_logC52EventExposureLedger` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1384 | `OpexAI::_logC54VehicleOrders` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1392 | `OpexAI::_logC54VehicleOrders` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1420 | `OpexAI::_recordC69BuildingPass` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1428 | `OpexAI::_recordC69BuildingPass` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1435 | `OpexAI::_recordC69BuildingPass` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1462 | `OpexAI::_recordC69BuildingPass` | D | `for` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/lines.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 74 | `OpexVehicleServesStation` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 99 | `OpexLineVehicleIds` | C | `for` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 111 | `OpexLineVehicleIds` | C | `for` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 120 | `OpexLineVehicleIds` | D | `for` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 129 | `OpexFindLineForVehicle` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 132 | `OpexFindLineForVehicle` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 138 | `OpexFindLineForVehicle` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 149 | `OpexFindLineForVehicle` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 159 | `OpexFindLineForVehicle` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 173 | `OpexFindLineForVehicle` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 203 | `OpexMedianInt` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 206 | `OpexMedianInt` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 299 | `OpexAI::_pruneAbandonedPairs` | D | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 308 | `OpexAI::_pruneAbandonedPairs` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 334 | `OpexAI::_tooClose` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 337 | `OpexAI::_tooClose` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 339 | `OpexAI::_tooClose` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 355 | `OpexAI::_tooClose` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 358 | `OpexAI::_tooClose` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 363 | `OpexAI::_tooClose` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 388 | `OpexAI::_tryAttachSharedDest` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 390 | `OpexAI::_tryAttachSharedDest` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 405 | `OpexAI::_tryAttachSharedDest` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 408 | `OpexAI::_tryAttachSharedDest` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 452 | `OpexAI::_findLineById` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/main.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 824 | `OpexAI::Start` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 870 | `OpexAI::Start` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 872 | `OpexAI::Start` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/opcode_exact.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 27 | `OpexRoadExcludeWithin` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 35 | `OpexRoadStopsTooClose` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 55 | `OpexRoadHistoricClassify` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 92 | `OpexRoadAccumulateFronts` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 116 | `OpexRoadAccumulateFronts` | D | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 152 | `OpexRoadSitesScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 153 | `OpexRoadSitesScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 154 | `OpexRoadSitesScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 273 | `OpexRoadVoirieTryFronts` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 293 | `OpexRoadVoirieTryFronts` | D | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 325 | `OpexRoadPaxVoirieScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 326 | `OpexRoadPaxVoirieScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 327 | `OpexRoadPaxVoirieScan` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 428 | `OpexRoadPlanForActive` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 456 | `OpexRoadPlanForActive` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 457 | `OpexRoadPlanForActive` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 460 | `OpexRoadPlanForActive` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 481 | `OpexRoadPlanForActive` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 482 | `OpexRoadPlanForActive` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 485 | `OpexRoadPlanForActive` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 519 | `OpexAirFleetSortPrecomputed` | D | `foreach` — L lignes possédées, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 524 | `OpexAirFleetSortPrecomputed` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 537 | `OpexAirCatchmentSumExact` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 569 | `OpexAirJoinedCandidatesExact` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 587 | `OpexAirJoinedCandidatesExact` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/orchestrator.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 100 | `toArray` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 307 | `OpexWorkerRailStockStep` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 380 | `OpexRailTargetIndustryHasStructuralPair` | D | `for` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 386 | `OpexRailTargetIndustryHasStructuralPair` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 391 | `OpexRailTargetIndustryHasStructuralPair` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 396 | `OpexRailTargetIndustryHasStructuralPair` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 407 | `OpexRailTargetIndustryHasStructuralPair` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 411 | `OpexRailTargetIndustryHasStructuralPair` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 425 | `OpexRailTargetIndustryHasStructuralPairForCargo` | D | `for` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 432 | `OpexRailTargetIndustryHasStructuralPairForCargo` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 437 | `OpexRailTargetIndustryHasStructuralPairForCargo` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 448 | `OpexRailTargetIndustryHasStructuralPairForCargo` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 452 | `OpexRailTargetIndustryHasStructuralPairForCargo` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 538 | `OpexRegenEntitySync` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 739 | `OpexAI::_c77EnqueueEntity` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 782 | `OpexAI::_v217RailRefill` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 783 | `OpexAI::_v217RailRefill` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 800 | `OpexAI::_v217RailRefill` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 915 | `OpexAI::_c77InjectSubsidy` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 917 | `OpexAI::_c77InjectSubsidy` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 925 | `OpexAI::_c77InjectSubsidy` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1122 | `OpexAI::_c76ModeNeedsRegen` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1166 | `OpexAI::_c76AcknowledgeAllLayers` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1171 | `OpexAI::_c76AcknowledgeAllLayers` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1225 | `OpexAC06AcknowledgeSnapshot` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1232 | `OpexAC06AcknowledgeSnapshot` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1349 | `OpexAI::_c80DoModeRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1358 | `OpexAI::_c80DoModeRegen` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1367 | `OpexAI::_c80DoModeRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1369 | `OpexAI::_c80DoModeRegen` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1379 | `OpexAI::_c76SaveRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1382 | `OpexAI::_c76SaveRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1392 | `OpexAI::_c76SaveRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1440 | `OpexAI::_c76LoadRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1443 | `OpexAI::_c76LoadRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1450 | `OpexAI::_c76LoadRevisions` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/pathfinder_v90/aystar.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 113 | `OpexAyStarV90::InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 126 | `OpexAyStarV90::InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 135 | `OpexAyStarV90::FindPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 149 | `OpexAyStarV90::FindPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 167 | `OpexAyStarV90::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 171 | `OpexAyStarV90::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 188 | `OpexAyStarV90::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/pathfinder_v90/binary_heap.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 75 | `OpexBinaryHeapV90::Insert` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 113 | `OpexBinaryHeapV90::Exists` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 128 | `OpexBinaryHeapV90::_BubbleDown` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/pathfinder_v90/rail.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 240 | `OpexRailPathFinderV90::InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 252 | `OpexRailPathFinderV90::InitializePath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 259 | `OpexRailPathFinderV90::InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 274 | `OpexRailPathFinderV90::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 488 | `OpexRailPathFinderV90::_Estimate` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 509 | `OpexRailPathFinderV90::_EstimateWeighted` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 535 | `OpexRailPathFinderV90::_Neighbours` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 542 | `OpexRailPathFinderV90::_Neighbours` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 561 | `OpexRailPathFinderV90::_Neighbours` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 608 | `OpexRailPathFinderV90::_GetTunnelsBridges` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 730 | `FindPath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 751 | `FindPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 799 | `FindPath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 840 | `FindPath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/pathfinder_v90/v129.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 50 | `OpexBinaryHeapV129::Insert` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 78 | `OpexBinaryHeapV129::Pop` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 111 | `OpexBinaryHeapV129::Exists` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 166 | `OpexAyStarV129::InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 183 | `OpexAyStarV129::InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 187 | `OpexAyStarV129::InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 209 | `OpexAyStarV129::FindPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 226 | `OpexAyStarV129::FindPath` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 244 | `OpexAyStarV129::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 248 | `OpexAyStarV129::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 269 | `OpexAyStarV129::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 279 | `OpexAyStarV129::FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 359 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 371 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 391 | `InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 392 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 403 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 411 | `InitializePath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 420 | `InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 437 | `FindPath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 465 | `_Estimate` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 486 | `_EstimateWeighted` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 658 | `_Neighbours` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 667 | `_Neighbours` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 675 | `_Neighbours` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 701 | `_TunnelsBridgesInto` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 772 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 796 | `FindPath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 839 | `FindPath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/pathfinder_v90/v296.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 42 | `Materialize` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 44 | `Materialize` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 57 | `FrontierAlternatives` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 72 | `_Finish` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 94 | `_InitializePathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 95 | `_InitializePathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 107 | `_InitializePathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 123 | `_InitializePathV296` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 124 | `_InitializePathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 135 | `_InitializePathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 143 | `_InitializePathV296` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 151 | `_InitializePathV296` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 161 | `_InitializePathV296` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 163 | `_InitializePathV296` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 220 | `OpexRailPathFinderV296::_FindPathV296` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 230 | `OpexRailPathFinderV296::_FindPathV296` | D | `while` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 240 | `OpexRailPathFinderV296::_FindPathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 257 | `OpexRailPathFinderV296::_FindPathV296` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 298 | `OpexRailPathFinderV296::_FindPathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 457 | `OpexRailPathFinderV296::_FindPathV296` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 499 | `InitializePath` | D | `foreach` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 511 | `InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 523 | `InitializePath` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 530 | `InitializePath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
| 532 | `InitializePath` | D | `for` — borne fonction/curseur, deux cartes | construction/chemin; n.m.; pas de substitution AIList directe; voisinage/construction, actions ou historique |
#### `ai/OpexAI/persist.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 41 | `OpexLoadRailExpansion` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 74 | `OpexCopyBoolTable` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 84 | `OpexSaveReactiveQueue` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 102 | `OpexLoadReactiveQueue` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 134 | `OpexSaveActiveWorker` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 175 | `OpexAI::_railLineHasVehicle` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 367 | `OpexAI::_filterPersistedRailRepairQueue` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 381 | `OpexAI::_rearmPersistedRailRepairTasks` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 406 | `OpexSaveC83Preempt` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 419 | `OpexSaveV250` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 423 | `OpexSaveV250` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 466 | `OpexLoadC121Strategy` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 475 | `OpexLoadC121Strategy` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 480 | `OpexLoadC121Strategy` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 494 | `OpexLoadC121Strategy` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 499 | `OpexLoadC121Strategy` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 560 | `OpexSaveProjectLine` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 596 | `OpexAI::_refreshSaveProjection` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 667 | `OpexAI::Save` | D | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 672 | `OpexAI::Save` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 687 | `OpexAI::Save` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 787 | `OpexAI::Load` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 840 | `OpexAI::Load` | D | `foreach` — S/H/voisins, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 880 | `OpexAI::Load` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 930 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 940 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 944 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — T villes (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 961 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 985 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 998 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1033 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1039 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1073 | `OpexAI::_reconcileAfterLoad` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1118 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1121 | `OpexAI::_reconcileAfterLoad` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/po01c_generators.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 22 | `OpexPO01CPaxCandidates` | C | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 31 | `OpexPO01CPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 44 | `OpexPO01CPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 58 | `OpexPO01CPaxCandidates` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 61 | `OpexPO01CPaxCandidates` | C | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 132 | `OpexPO01CFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 139 | `OpexPO01CFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 148 | `OpexPO01CFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 156 | `OpexPO01CFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 208 | `OpexPO01CFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 273 | `OpexPO01CRoadFreightCandidates` | D | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 279 | `OpexPO01CRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 294 | `OpexPO01CRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 307 | `OpexPO01CRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 314 | `OpexPO01CRoadFreightCandidates` | C | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 319 | `OpexPO01CRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 333 | `OpexPO01CRoadFreightCandidates` | C | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 369 | `OpexPO01CRoadFreightCandidates` | D | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 376 | `OpexPO01CRoadFreightCandidates` | C | `for` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 462 | `OpexPO01CWaterPlans` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 475 | `OpexPO01CWaterPlans` | D | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 499 | `OpexPO01CWaterPlans` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 501 | `OpexPO01CWaterPlans` | C | `for` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 577 | `OpexPO01CWaterPlans` | D | `while` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 592 | `OpexPO01CWaterPlans` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 610 | `OpexPO01CCargos` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 648 | `OpexPO01CRail` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 665 | `OpexPO01CRail` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 743 | `OpexPO01CRail` | D | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 747 | `OpexPO01CRail` | D | `while` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 754 | `OpexPO01CRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 757 | `OpexPO01CRail` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 765 | `OpexPO01CRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 778 | `OpexPO01CRail` | H | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 818 | `OpexPO01CRail` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 822 | `OpexPO01CRail` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 837 | `OpexPO01CTowns` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 852 | `OpexPO01CTowns` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 874 | `OpexPO01CIndustries` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 887 | `OpexPO01CIndustries` | D | `for` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 899 | `OpexPO01CIndustries` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 904 | `OpexPO01CIndustries` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 939 | `OpexPO01CAir` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 944 | `OpexPO01CAir` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 990 | `OpexPO01CAir` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 995 | `OpexPO01CAir` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1055 | `OpexPO01CWater` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1097 | `OpexPO01CRoad` | C | `for` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1112 | `OpexPO01CRoad` | C | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 1116 | `OpexPO01CRoad` | C | `foreach` — V/E selon partie/NewGRF, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/po01c_regen.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 30 | `OpexPO01CGenerateMode` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 33 | `OpexPO01CGenerateMode` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 36 | `OpexPO01CGenerateMode` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 41 | `OpexPO01CGenerateMode` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 54 | `OpexPO01CGenerateMode` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 60 | `OpexPO01CGenerateMode` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 62 | `OpexPO01CGenerateMode` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 68 | `OpexPO01CGenerateMode` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 81 | `OpexPO01CCopyLines` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 84 | `OpexPO01CCopyLines` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 96 | `OpexPO01CLineState` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 100 | `OpexPO01CLineState` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 105 | `OpexPO01CLineState` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 107 | `OpexPO01CLineState` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 129 | `OpexPO01CAirPending` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 178 | `OpexPO01CStart` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 180 | `OpexPO01CStart` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 189 | `OpexPO01CStart` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 195 | `OpexPO01CStart` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 200 | `OpexPO01CStart` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 200 | `OpexPO01CStart` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 213 | `OpexPO01CAcknowledge` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 218 | `OpexPO01CAcknowledge` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 222 | `OpexPO01CAcknowledge` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 233 | `OpexPO01CAcknowledge` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 235 | `OpexPO01CAcknowledge` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 237 | `OpexPO01CAcknowledge` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 252 | `OpexPO01CAcknowledge` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 262 | `OpexPO01CPublish` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 264 | `OpexPO01CPublish` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 271 | `OpexPO01CPublish` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 276 | `OpexPO01CPublish` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 287 | `OpexPO01CPublish` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 289 | `OpexPO01CPublish` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 303 | `OpexPO01CMerge` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 305 | `OpexPO01CMerge` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 311 | `OpexPO01CMerge` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 324 | `OpexPO01CLog` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 325 | `OpexPO01CLog` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 378 | `OpexPO01CStep` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 380 | `OpexPO01CStep` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 389 | `OpexPO01CStep` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 404 | `OpexPO01CStep` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 419 | `OpexPO01CStep` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/probe_v216.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 22 | `OpexV216SelectionWanted` | D | `for` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 48 | `OpexV216Pick` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 105 | `OpexV216LogSelection` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 113 | `OpexV216LogSelection` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 125 | `OpexV216LogSelection` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 132 | `OpexV216LogSelection` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 133 | `OpexV216LogSelection` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 182 | `OpexV216MonthlyTick` | D | `foreach` — T villes (256² / 1024²) | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 185 | `OpexV216MonthlyTick` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 199 | `OpexV216MonthlyTick` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 200 | `OpexV216MonthlyTick` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 209 | `OpexV216MonthlyTick` | D | `foreach` — N_gares par compagnie, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 216 | `OpexV216MonthlyTick` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 233 | `OpexV216Cargo` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 247 | `OpexV216NoteReject` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 259 | `OpexV216FlushRejects` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 305 | `OpexV216MarkRect` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 306 | `OpexV216MarkRect` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 336 | `OpexV216RefreshCover` | D | `foreach` — N_gares par compagnie, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 340 | `OpexV216RefreshCover` | D | `foreach` — N_gares par compagnie, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 344 | `OpexV216RefreshCover` | D | `foreach` — N_gares par compagnie, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 373 | `OpexV216AdvAround` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 398 | `OpexV216Coverage` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 399 | `OpexV216Coverage` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/probe_v262_orphans.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 47 | `OpexV262NoteLineStations` | D | `for` — L lignes possédées, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 70 | `OpexV262CountDepots` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 103 | `OpexV262OrphanSurvey` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 105 | `OpexV262OrphanSurvey` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 114 | `OpexV262OrphanSurvey` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 119 | `OpexV262OrphanSurvey` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 121 | `OpexV262OrphanSurvey` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 130 | `OpexV262OrphanSurvey` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 152 | `OpexV262OrphanSurvey` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 153 | `OpexV262OrphanSurvey` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 161 | `OpexV262OrphanSurvey` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/probe_v307.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 41 | `OpexV307Pairs` | D | `for` — T villes (256² / 1024²) | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 44 | `OpexV307Pairs` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 45 | `OpexV307Pairs` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 55 | `OpexV307Pairs` | D | `for` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 80 | `OpexV307FreightPairs` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 88 | `OpexV307FreightPairs` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 90 | `OpexV307FreightPairs` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 106 | `OpexV307FreightPairs` | D | `for` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 127 | `OpexV307Block` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 167 | `OpexV307Coarse` | D | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 176 | `OpexV307Coarse` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 195 | `OpexV307Coarse` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 212 | `OpexV307Guide` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 214 | `OpexV307Guide` | H | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 215 | `OpexV307Guide` | H | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 220 | `OpexV307Guide` | H | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 222 | `OpexV307Guide` | H | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 240 | `OpexV307PathCost` | D | `foreach` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 258 | `OpexV307Search` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 277 | `OpexV307Log` | D | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 329 | `OpexV307EndpointScout` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 330 | `OpexV307EndpointScout` | D | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 346 | `OpexV307OctantCount` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 356 | `OpexV307EndpointOne` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 369 | `OpexV307EndpointOne` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 372 | `OpexV307EndpointOne` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 378 | `OpexV307EndpointOne` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 384 | `OpexV307EndpointOne` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 389 | `OpexV307EndpointOne` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 408 | `OpexV307RailType` | A | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; AIList/Valuate API possible; min/max/tri simple de liste déjà native |
| 433 | `OpexV307LongProbe` | D | `foreach` — S/H/voisins, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/probe_v308.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 56 | `OpexV308RiverCrosses` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 58 | `OpexV308RiverCrosses` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 63 | `OpexV308RiverCrosses` | D | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 71 | `OpexV308RiverCrosses` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 88 | `OpexV308Truth` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 89 | `OpexV308Truth` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 106 | `OpexV308Arm` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 109 | `OpexV308Arm` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 119 | `OpexV308Arm` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 147 | `OpexV308CartoProbe` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/probes.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 60 | `OpexV251CargoLabels` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 78 | `OpexV251LogIndustryTypes` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 84 | `OpexV251LogIndustryTypes` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 165 | `OpexRailPortfolioAudit` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 175 | `OpexRailPortfolioAudit` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 296 | `OpexC121HubDelayFlushLine` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 348 | `OpexC121FirstLiveAggregate` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 408 | `OpexC121FirstLiveObserve` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 530 | `OpexC117AirThroughputStep` | D | `foreach` — L lignes possédées, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 553 | `OpexC117AirThroughputStep` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 914 | `OpexC78FundedRank` | D | `for` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 942 | `OpexAI::_c78SlotOnProjectsPass` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 944 | `OpexAI::_c78SlotOnProjectsPass` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1257 | `OpexC63EnsureYear` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1305 | `OpexC63NotePass` | D | `for` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1323 | `OpexC63NotePass` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1386 | `OpexC63FlushLedger` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1569 | `OpexC49IsMapFailure` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1731 | `OpexC39CatalogUsesEngine` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1732 | `OpexC39CatalogUsesEngine` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1734 | `OpexC39CatalogUsesEngine` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1737 | `OpexC39CatalogUsesEngine` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1739 | `OpexC39CatalogUsesEngine` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1787 | `OpexC69VehicleProfitLastYear` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1801 | `OpexMedianFloat` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1802 | `OpexMedianFloat` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1805 | `OpexMedianFloat` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1839 | `OpexComputeOperatingCashFlow` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1877 | `OpexC69ComputeKDec` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1919 | `OpexC75RecordPassDate` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1944 | `OpexC75ComputeKPass` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2253 | `OpexC73RecordSelection` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2278 | `OpexC73FlushLedger` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2281 | `OpexC73FlushLedger` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2398 | `OpexC76GetBuildableEngines` | D | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2410 | `OpexC76CountEngineChanges` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2413 | `OpexC76CountEngineChanges` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2431 | `OpexC76FlushYear` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2436 | `OpexC76FlushYear` | H | `for` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2492 | `OpexV309IdleProjects` | D | `foreach` — N_vivier/K, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2685 | `OpexLoopProfFlushIfNewYear` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2699 | `OpexAI::_mainLoopProfiled` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2747 | `OpexAI::_mainLoopProfiled` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2749 | `OpexAI::_mainLoopProfiled` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2828 | `OpexSpanFlushAgg` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2890 | `OpexSpanEnd` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2911 | `OpexSpanRescueOrphans` | H | `while` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/projects.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 102 | `OpexMergeRailCandidateSet` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 108 | `OpexMergeRailCandidateSet` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 215 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 224 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 232 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 249 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 254 | `OpexBuildProjects` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 258 | `OpexBuildProjects` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 311 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 341 | `OpexBuildProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 354 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 362 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 414 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 454 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 465 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 473 | `OpexBuildProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 476 | `OpexBuildProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 480 | `OpexBuildProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 495 | `OpexBuildProjects` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 514 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 516 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 540 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 564 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 565 | `OpexBuildProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_builders.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 53 | `OpexC80ProjectBelowMarginalFloor` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_diagnostics.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 13 | `OpexB6LogSelectionCausality` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 26 | `OpexB6LogSelectionCausality` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 70 | `OpexB6LogSelectionCausality` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 123 | `OpexB6FreshBucket` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 125 | `OpexB6FreshBucket` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 199 | `OpexB6LogFreshEquivalence` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 202 | `OpexB6LogFreshEquivalence` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 204 | `OpexB6LogFreshEquivalence` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 208 | `OpexB6LogFreshEquivalence` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 217 | `OpexB6LogFreshEquivalence` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 225 | `OpexB6LogFreshEquivalence` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 240 | `OpexB6LogFreshEquivalence` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/projects_generation.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 30 | `OpexGenerateModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 35 | `OpexGenerateModeProjects` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 38 | `OpexGenerateModeProjects` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 69 | `OpexGenerateModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 81 | `OpexGenerateModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 99 | `OpexGenerateModeProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 112 | `OpexGenerateModeProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 130 | `OpexApplyGeneratedModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 132 | `OpexApplyGeneratedModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 140 | `OpexApplyGeneratedModeProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 229 | `OpexRegenerateAirProjectsSlice` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 288 | `OpexCandidateStillValid` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 434 | `OpexIncrRevalidateIndexContext` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 453 | `OpexIncrRevalidateIndexContext` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 457 | `OpexIncrRevalidateIndexContext` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 461 | `OpexIncrRevalidateIndexContext` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 662 | `OpexAir0310FilterAirAlternativesStillValid` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 716 | `OpexRailPrepMergeAlternatives` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 730 | `OpexRailPrepMergeAlternatives` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_models.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 46 | `OpexC70RecomputeFactors` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 53 | `OpexC70RecomputeFactors` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 92 | `OpexC121ApplyRealizationSums` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 120 | `OpexC121RecomputeRealizationFactors` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_rank_log.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 11 | `OpexLogPortfolioRank` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 46 | `OpexLogPortfolioRankWithTension` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 52 | `OpexLogPortfolioRankWithTension` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 65 | `OpexLogPortfolioRankWithTension` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 83 | `OpexLogPortfolioRankWithTension` | D | `foreach` — L lignes possédées, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_selection.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 147 | `OpexEarlySlotSelectionState` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 174 | `OpexDefensiveSlotSelectionState` | C | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 221 | `OpexC121PressureAdvanceYear` | D | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 289 | `OpexC121RecordPressureSnapshot` | D | `foreach` — T villes (256² / 1024²) | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 706 | `OpexSelectRejectLog` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 748 | `OpexProjectSelectAffordable` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 796 | `OpexProjectSelectAffordable` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 865 | `OpexProjectSelectAffordable` | C | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 917 | `OpexProjectSelectAffordable` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 925 | `OpexProjectSelectAffordable` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 934 | `OpexProjectSelectAffordable` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 937 | `OpexProjectSelectAffordable` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 987 | `OpexProjectInsertDefensive` | D | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1032 | `OpexProjectInsertDefensive` | D | `while` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1091 | `OpexPromoteLiveDefensiveAir` | D | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1168 | `OpexLogVivier` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1199 | `OpexProjectsStampSelectionStats` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1215 | `OpexProjectsStampSelectionStats` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1318 | `OpexFilterAirAlternativesV279Memo` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1431 | `OpexReselectProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1432 | `OpexReselectProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1468 | `OpexReselectProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1501 | `OpexReselectProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1502 | `OpexReselectProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1566 | `OpexProjectsRecountGroups` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/projects_update.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 16 | `OpexInjectFleetProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 18 | `OpexInjectFleetProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 28 | `OpexInjectFleetProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 91 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 93 | `OpexIncrementalUpdateProjects` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 134 | `OpexIncrementalUpdateProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 158 | `OpexIncrementalUpdateProjects` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 173 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 175 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 202 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 223 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 224 | `OpexIncrementalUpdateProjects` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 275 | `OpexAir0310InsertAirBlock` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 277 | `OpexAir0310InsertAirBlock` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 283 | `OpexAir0310InsertAirBlock` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 292 | `OpexAir0310PriorDropped` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 296 | `OpexAir0310PriorDropped` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 330 | `OpexV277AirPubFastInsert` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 331 | `OpexV277AirPubFastInsert` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 339 | `OpexV277AirPubFastInsert` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 398 | `OpexAir0310PublishIncremental` | D | `for` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 421 | `OpexAir0310PublishIncremental` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 449 | `OpexAir0310PublishIncremental` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 472 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 474 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 489 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 493 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 538 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 541 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 558 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 562 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 573 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 574 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 575 | `OpexAir0310PublishIncremental` | H | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 576 | `OpexAir0310PublishIncremental` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 580 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 583 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 586 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 595 | `OpexAir0310PublishIncremental` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 596 | `OpexAir0310PublishIncremental` | D | `foreach` — S/H/voisins, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 620 | `OpexAir0310PublishIncremental` | D | `foreach` — N_vivier/K, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 630 | `OpexAir0310PublishIncremental` | H | `for` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 640 | `OpexAir0310PublishIncremental` | D | `foreach` — borne fonction/curseur, deux cartes | passe/regen ou tranche; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/rail_long_window_probe.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 17 | `OpexRLW03TopTownCohort` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 28 | `OpexRLW03ReachedTowns` | D | `foreach` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 43 | `OpexRLW03ReachedTowns` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 61 | `OpexRLW03ShortPool` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 62 | `OpexRLW03ShortPool` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 90 | `OpexRLW03Growth` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 91 | `OpexRLW03Growth` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/rail_prep_c121.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 23 | `OpexAI::_c121CheapestLivingAirCap` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 25 | `OpexAI::_c121CheapestLivingAirCap` | D | `foreach` — N_vivier/K, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 251 | `OpexAI::_tryStartC121RailPrepSearch` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/rail_templates.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 142 | `OpexSourceTemplateTiles` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 143 | `OpexSourceTemplateTiles` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 162 | `OpexDestTemplateTiles` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 178 | `OpexTemplateCheckOrLevel` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 218 | `OpexSourceRails` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 237 | `OpexSourceRails` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 298 | `OpexFindSourceTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 299 | `OpexFindSourceTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 300 | `OpexFindSourceTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 307 | `OpexFindSourceTemplateSite` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 325 | `OpexFindDestTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 326 | `OpexFindDestTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 327 | `OpexFindDestTemplateSite` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 334 | `OpexFindDestTemplateSite` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 361 | `OpexBuildSourceTemplateReal` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 380 | `OpexBuildSourceTemplateReal` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 407 | `OpexBuildSourceTemplateReal` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 444 | `OpexBuildDestTemplateReal` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 457 | `OpexBuildDestTemplateReal` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 479 | `OpexBuildDestTemplateReal` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 516 | `OpexDemolishSourceTemplate` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 523 | `OpexDemolishSourceTemplate` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 540 | `OpexDemolishDestTemplate` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 547 | `OpexDemolishDestTemplate` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 560 | `OpexDemolishTrack` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 576 | `OpexBuildBlockSignals` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 716 | `OpexV198ExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 717 | `OpexV198ExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 718 | `OpexV198ExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 720 | `OpexV198ExecuteRailPlan` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 724 | `OpexV198ExecuteRailPlan` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 799 | `OpexV198ExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 804 | `OpexV198ExecuteRailPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/rivals_v211.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 19 | `OpexV211QuarterlyTick` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 43 | `OpexV211QuarterlyTick` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 45 | `OpexV211QuarterlyTick` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 71 | `OpexV211SelfScore` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 81 | `OpexV211SelfScore` | D | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 82 | `OpexV211SelfScore` | D | `foreach` — N_gares par compagnie, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 92 | `OpexV211SelfScore` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 110 | `OpexV211SelfScore` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 124 | `OpexV211Word` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/scheduler.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 197 | `OpexAI::_runNextTask` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 208 | `OpexAI::_runNextTask` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 439 | `OpexAI::_advanceRailSearchThroughput` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/scheduler_tasks.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 104 | `OpexV147ArmPhases` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 127 | `OpexV147PhaseTask` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 734 | `OpexAI::_dispatchC41RailSignals` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 765 | `OpexAI::_dispatchC41RailJunction` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/selftests.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 202 | `OpexAI::_c80RunSelfTest` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 207 | `OpexAI::_c80RunSelfTest` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/settings.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 483 | `OpexLoadSettings` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/spatial.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 13 | `OpexIsqrt` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 53 | `OpexSpatialGrid::Build` | C | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 82 | `OpexSpatialGrid::GetCandidatesAt` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 83 | `OpexSpatialGrid::GetCandidatesAt` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 87 | `OpexSpatialGrid::GetCandidatesAt` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 111 | `OpexIndustryPrimaryRivalServed` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 143 | `OpexStationEncroachesRival` | C | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/task_air.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 19 | `OpexAirBatchHubHasCapacity` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 59 | `OpexAirBatchPlanStillLive` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 74 | `OpexAirTownServedIndexed` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 186 | `OpexAI::_tryBuildAirProject` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 307 | `OpexAI::_tryBuildAirProject` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 470 | `OpexAI::_resizeAirFleets` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 502 | `OpexAI::_resizeAirFleets` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 666 | `OpexAI::_resizeAirFleets` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 692 | `OpexAI::_resizeAirFleets` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 758 | `OpexAI::_resizeAirFleets` | D | `while` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/task_projects.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 12 | `OpexR1R3FleetTrace` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 93 | `OpexAI::_recordMonthlyFunnelPass` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 147 | `OpexAI::_recordMonthlyFunnelPass` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 150 | `OpexAI::_recordMonthlyFunnelPass` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 169 | `OpexAI::_purgeSubsidyFromProjects` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 181 | `OpexAI::_purgeSubsidyFromProjects` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 291 | `OpexAI::_tryBuildFleetProject` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 392 | `OpexAI::_c39StampFinanceable` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 421 | `OpexAirC83FundedRaceCoversTown` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 447 | `OpexC122ThreatFundedMatch` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 590 | `OpexC122ThreatProjectTowns` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 601 | `OpexC122ThreatNoteAttempt` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 619 | `OpexC122ThreatNoteOutcome` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 630 | `OpexC122ThreatNoteOutcome` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 652 | `OpexC122ThreatRetryUnbuildable` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 832 | `OpexC83WatchAirSlots` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 838 | `OpexC83WatchAirSlots` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 841 | `OpexC83WatchAirSlots` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 955 | `OpexAI::_c83WatchAirSlotTransitions` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 960 | `OpexAI::_c83WatchAirSlotTransitions` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1002 | `OpexAI::_c83WatchAirSlotTransitions` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1085 | `OpexAI::_projectsRankOfAttemptKey` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1132 | `OpexAI::_recordPortfolioProjectBuilt` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1217 | `OpexAI::_consumeResumableRailAtPassStart` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1256 | `OpexAI::_consumeResumableRailAtPassStart` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1501 | `OpexAI::_tryBuildProjects` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1738 | `OpexAI::_tryBuildProjects` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1758 | `OpexAI::_tryBuildProjects` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1937 | `OpexAI::_tryBuildProjects` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2100 | `OpexAI::_rebuildProjects` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2126 | `OpexAI::_rebuildProjects` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_rail.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 75 | `OpexC41RailLocalLinks` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 116 | `OpexC41RepairJunction` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 325 | `OpexAI::_tryBuildRailProject` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 365 | `OpexAI::_tryBuildRailProject` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 417 | `OpexAI::_expandRailLines` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 526 | `OpexAI::_expandRailLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 985 | `OpexAI::_continueRailSearch` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1289 | `OpexAI::_recordRailAttempt` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1303 | `OpexAI::_recordRailAttempt` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1477 | `OpexAI::_consumeRailUpgrade` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1797 | `OpexV131ScanBlocked` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1807 | `OpexV131ScanBlocked` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1812 | `OpexV131ScanBlocked` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 1827 | `OpexV131CountBlocked` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1838 | `OpexV131RawRuns` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1844 | `OpexV131RawRuns` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1856 | `OpexV131MergedRuns` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1898 | `OpexV131PlatformsOverlap` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1904 | `OpexV131PlatformsOverlap` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1931 | `OpexV131SidewaysShift` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1932 | `OpexV131SidewaysShift` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1934 | `OpexV131SidewaysShift` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1939 | `OpexV131SidewaysShift` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1968 | `OpexV131PickFresh` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1990 | `OpexV131FindShift` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2022 | `OpexV131CanBranchOut` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2039 | `OpexV131CanBranchIn` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2070 | `OpexV131PlanAnchorRun` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2104 | `OpexV131PlanAnchorRun` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; curseur et suspension à conserver |
| 2168 | `OpexV131IgnoreForRun` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2171 | `OpexV131IgnoreForRun` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2187 | `OpexV131IgnoreForRun` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2199 | `OpexV131IgnoreForRun` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2276 | `OpexV131SplicePrefix` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2281 | `OpexV131SplicePrefix` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2296 | `OpexV131SpliceSuffix` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2301 | `OpexV131SpliceSuffix` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2316 | `OpexV131SpliceSpan` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2321 | `OpexV131SpliceSpan` | H | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2326 | `OpexV131SpliceSpan` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2344 | `OpexV131ApplySplice` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 2375 | `OpexV131RebuildStructures` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2448 | `OpexAI::_v131DropDuplicateOwnRail` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2518 | `OpexAI::_v131PlanRepairs` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 2792 | `OpexAI::_revalidateRailStockPlan` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2794 | `OpexAI::_revalidateRailStockPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2853 | `OpexAI::_revalidateRailStockPlan` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 2855 | `OpexAI::_revalidateRailStockPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_report.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 102 | `OpexC70PublishModeFactors` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 219 | `OpexAI::_reportLines` | D | `for` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 256 | `OpexAI::_reportLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 319 | `OpexAI::_reportLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 340 | `OpexAI::_reportLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 487 | `OpexAI::_reportLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 507 | `OpexAI::_reportLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 564 | `OpexAI::_reportLines` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 584 | `OpexAI::_reportLines` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 590 | `OpexAI::_reportLines` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 662 | `OpexAI::_triggerScrapLine` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 683 | `OpexAI::_scrapDeadLines` | D | `for` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 693 | `OpexAI::_scrapDeadLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 722 | `OpexAI::_scrapDeadLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 742 | `OpexAI::_scrapDeadLines` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 759 | `OpexAI::_scrapRetiredVehicles` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 799 | `OpexAI::_scrapRetiredVehicles` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 847 | `OpexAI::_scrapRetiredVehicles` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 850 | `OpexAI::_scrapRetiredVehicles` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 856 | `OpexAI::_scrapRetiredVehicles` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 867 | `OpexAI::_purgeUnprofitableStreaks` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 870 | `OpexAI::_purgeUnprofitableStreaks` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 885 | `OpexAI::_reportYear` | D | `for` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 889 | `OpexAI::_reportYear` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 897 | `OpexAI::_reportYear` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 936 | `OpexAI::_reportYear` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1088 | `OpexAI::_reportC78Candidates` | D | `for` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1099 | `OpexAI::_reportC78Candidates` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1101 | `OpexAI::_reportC78Candidates` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1106 | `OpexAI::_reportC78Candidates` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1123 | `OpexAI::_reportC78Candidates` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1157 | `OpexAI::_c76RecordRegen` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1166 | `OpexAI::_c76RecordRegen` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1169 | `OpexAI::_c76RecordRegen` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1178 | `OpexAI::_c76RecordRegen` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1186 | `OpexAI::_c76RecordRegen` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1187 | `OpexAI::_c76RecordRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1199 | `OpexAI::_c76RecordRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1202 | `OpexAI::_c76RecordRegen` | D | `foreach` — I/P/Q selon cargo (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1229 | `OpexAI::_c76RecordRegen` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1233 | `OpexAI::_c76RecordRegen` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1248 | `OpexAI::_c76RecordRegen` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1250 | `OpexAI::_c76RecordRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1265 | `OpexAI::_c76RecordRegen` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1280 | `OpexAI::_c76RecordRegen` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 1300 | `OpexAI::_c76RecordRegen` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1322 | `OpexAI::_c76RecordRegen` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1329 | `OpexAI::_c76RecordRegen` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1363 | `OpexAI::_c76RecordRegen` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1481 | `OpexAI::_v292TryBuildHq` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1495 | `OpexAI::_v292TryBuildHq` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1502 | `OpexAI::_v292TryBuildHq` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1550 | `OpexAI::_v292TryBuildHq` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1552 | `OpexAI::_v292TryBuildHq` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 1571 | `OpexAI::_v292TryBuildHq` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_road.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 193 | `OpexAI::_tryBuildRoadProject` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 300 | `OpexAI::_refleetRoadLines` | D | `for` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 332 | `OpexAI::_refleetRoadLines` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_terrain.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 46 | `OpexAI::_c67NoteNewLines` | D | `while` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 61 | `OpexAI::_c67FeedBackground` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 179 | `OpexAI::_c67WaterNextQuery` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 181 | `OpexAI::_c67WaterNextQuery` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 187 | `OpexAI::_c67WaterNextQuery` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 238 | `OpexAI::_c67WaterExposureStep` | D | `while` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/task_v249.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 20 | `OpexV249MaxListedCapital` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 31 | `OpexV249BestAdmissibleCapital` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 53 | `OpexV249GetPendingV252Cost` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 60 | `OpexV249GetPendingV252Cost` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 65 | `OpexV249GetPendingV252Cost` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 88 | `OpexV249GetPendingV252Cost` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 121 | `OpexV249LineProfit` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 148 | `OpexV249LineServiceInfo` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 201 | `OpexV249DispatchMode2` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 210 | `OpexV249DispatchMode2` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 220 | `OpexV249DispatchMode2` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 249 | `OpexV249DispatchMode2` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 267 | `OpexV249DispatchMode2` | D | `foreach` — N_gares par compagnie, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 273 | `OpexV249DispatchMode2` | D | `foreach` — N_gares par compagnie, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 274 | `OpexV249DispatchMode2` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 295 | `OpexV249DispatchMode2` | D | `foreach` — N_gares par compagnie, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 308 | `OpexV249DispatchMode2` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 410 | `OpexAI::_dispatchV249Statue` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 415 | `OpexAI::_dispatchV249Statue` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 436 | `OpexAI::_dispatchV249Statue` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_v250.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 71 | `OpexV250InsertByPop` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 82 | `OpexV250SampleTown` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 92 | `OpexV250TargetCount` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 113 | `OpexV250Watch` | C | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 125 | `OpexV250Contested` | C | `for` — N_gares par compagnie, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 133 | `OpexV250Contested` | C | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 158 | `OpexV250RunNormal` | C | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 182 | `OpexV250TargetedOrder` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 188 | `OpexV250TargetedOrder` | B | `for` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; valuation de valeur API puis tri/filtre natif |
| 193 | `OpexV250TargetedOrder` | C | `for` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 195 | `OpexV250TargetedOrder` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 203 | `OpexV250TargetedOrder` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 217 | `OpexV250RunTest` | C | `for` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 232 | `OpexV250RunTest` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 244 | `OpexV250BuyOrdered` | H | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 246 | `OpexV250BuyOrdered` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 247 | `OpexV250BuyOrdered` | D | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 251 | `OpexV250BuyOrdered` | C | `foreach` — T villes (256² / 1024²) | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 266 | `OpexV250BuyOrdered` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 272 | `OpexV250BuyOrdered` | C | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
#### `ai/OpexAI/task_v252.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 42 | `OpexAI::_dispatchV252AirEngineRefresh` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 50 | `OpexAI::_dispatchV252AirEngineRefresh` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 56 | `OpexAI::_dispatchV252AirEngineRefresh` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 79 | `OpexAI::_dispatchV252AirEngineRefresh` | D | `foreach` — N_vivier/K, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 149 | `OpexAI::_dispatchV252AirEngineRefresh` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_v257.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 202 | `OpexV257BestPlan` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 217 | `OpexV257BestPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 218 | `OpexV257BestPlan` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 219 | `OpexV257BestPlan` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 253 | `OpexAI::_v257Review` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 301 | `OpexAI::_v257Review` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 311 | `OpexAI::_v257Review` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 489 | `OpexAI::_v257ReplaceStep` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 515 | `OpexAI::_v257ReplaceStep` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 526 | `OpexAI::_v257ReplaceStep` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 559 | `OpexV257Reconcile` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 580 | `OpexV257Reconcile` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 597 | `OpexV257Reconcile` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_v259.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 22 | `OpexV259SaveQueue` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 42 | `OpexV259LoadQueue` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 48 | `OpexV259LoadQueue` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 71 | `OpexV259LineProfit` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 86 | `OpexV259LineMaxVehicleSpeed` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 108 | `OpexV259LineRemainingYears` | D | `foreach` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 170 | `OpexAI::_v259PrepareBridgeQueue` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 177 | `OpexAI::_v259PrepareBridgeQueue` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_v284.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 37 | `OpexV284Equipment` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 67 | `OpexV284Select` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 84 | `OpexV284Select` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 160 | `OpexV284Trace` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 181 | `OpexV284Trace` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 211 | `OpexV284LoopPlan` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 217 | `OpexV284LoopPlan` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 235 | `OpexV284LoopPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 237 | `OpexV284LoopPlan` | D | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 251 | `OpexV284LoopPlan` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 257 | `OpexV284LoopPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 269 | `OpexV284LoopPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 280 | `OpexV284LoopPlan` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 293 | `OpexV284BuildLoop` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 297 | `OpexV284BuildLoop` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 300 | `OpexV284BuildLoop` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 304 | `OpexV284BuildLoop` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 317 | `OpexV284RollbackLoop` | D | `foreach` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 322 | `OpexV284RollbackLoop` | D | `for` — S/H/voisins, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 340 | `OpexV284Adopt` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 379 | `OpexV284Tick` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 434 | `OpexV284Tick` | D | `for` — V/E selon partie/NewGRF, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/task_v294h.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 41 | `OpexV294hIsDeferred` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 104 | `OpexV294hAdvance` | D | `while` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 138 | `OpexV294hFinish` | H | `for` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/task_water.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 54 | `OpexAI::_tryBuildWaterProject` | D | `foreach` — borne fonction/curseur, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 96 | `OpexAI::_refleetCrashedWaterLines` | D | `foreach` — L lignes possédées, deux cartes | tick/tranche ou événement; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
#### `ai/OpexAI/tension.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 108 | `OpexTensionFleetScan` | D | `for` — V/E selon partie/NewGRF, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 157 | `OpexTensionContext` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 313 | `OpexTensionVector` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/terrain_map.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 126 | `_fresh` | H | `foreach` — rectangle/voisinage local sur 256² et 1024² | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 266 | `Step` | D | `while` — I/P/Q selon cargo (256² / 1024²) | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
#### `ai/OpexAI/terrain_valuate.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 149 | `ReadBlock` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 365 | `ReadBlockInstrumented` | D | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 448 | `ReadBlockReference` | C | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 449 | `ReadBlockReference` | C | `for` — rectangle/voisinage local sur 256² et 1024² | sonde si activée; n.m.; AIList/Valuate API possible; préfiltrage API éventuel, décision/ordre conservés |
| 512 | `CompareSummaries` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 519 | `CompareSummaries` | H | `foreach` — borne fonction/curseur, deux cartes | sonde si activée; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
#### `ai/OpexAI/water_graph.nut`

| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |
|---:|---|:---:|---|---|
| 84 | `_record` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 128 | `_beginJob` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 135 | `_find` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 191 | `_publishJob` | D | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |
| 285 | `_push` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 317 | `_unitQuery` | H | `while` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 327 | `_unitQuery` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 339 | `_unitQuery` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 365 | `Step` | D | `while` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 381 | `CorridorBlocks` | H | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 384 | `CorridorBlocks` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 384 | `CorridorBlocks` | H | `for` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; contrôle/constantes hors parcours d'entités |
| 441 | `Step` | D | `while` — L lignes possédées, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; état cumulatif, recherche, tri ou sortie anticipée |
| 447 | `Step` | D | `foreach` — borne fonction/curseur, deux cartes | appel métier/rapport; n.m.; pas de substitution AIList directe; objets Squirrel/effets par élément ou ordre observable |

<!-- INDEX_END -->
