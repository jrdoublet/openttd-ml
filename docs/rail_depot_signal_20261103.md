# RAIL-DEPOT-SIGNAL — diagnostic, expérience et qualification (3 novembre 2026)

**État actualisé au terme des bancs du 3 novembre 2026 :** smokes RDS 4×6 et contrôle 40×5 **effectivement exécutés**, Docker réparé par l'orchestrateur. Les 26 trains perdus du RDS initial restent un défaut physique prouvé. Une garde **fail-closed** empêche désormais la création d'embranchements PBS non certifiés et replie la construction sur le dépôt historique, sans modifier le défaut `rail_depot_signal=0`. Le 40×5 de ce repli est **négatif et non significatif** : Δ `profit_year` **−12 257,95 £/an**, p=0,4683 ; **aucune branche RDS nouvelle n'a été exposée**. La porte B n'est pas admissible. Les constats historiques devenus obsolètes des §§1–8 sont conservés pour traçabilité ; **le §9 fait foi pour la conclusion**. Ne pas prétendre que le bug YAPF/PBS est corrigé ou que l'objectif de parité avec AAA est atteint.

## Cadrage et pré-enregistrement, avant les bancs

- Projet : `/openttd-ml/.wt_sibling_20261102`, branche `exp/rail-sibling-20261102`, base Git `99f29d9c858f390de6193978a4f12d3fbdb48127` **avec changements locaux préexistants conservés** ; aucune fusion, commit, publication, stash, reset ou modification de défaut.
- `rail_depot_signal` ajouté aux quatre difficultés avec **défaut 0**. Un seul arbre IA et un seul bundle comparés : OFF=0 versus ON=1 ; autres options identiques. Source gelée avant intervention par les six SHA-256 de `sweeps/fixtures/rail_depot_signal_off.json` ; reconstruction OFF exacte exigée.
- Type : comportemental, éventuellement dépense de construction et opcodes supplémentaires. Métrique primaire : **`profit_year` d'OpexAI ON − OpexAI OFF** à l'horizon ; vérifier aussi l'écart de profit propre ON et non la seule baisse d'AAAHogEx. Valeur de compagnie = garde purement descriptive avec `--value-guard-max-loss-pct 100` (décision utilisateur). Bootstrap IC95 et Wilcoxon exact calculés par harnais.
- Smoke préenregistré : **4 graines × 6 ans**, graines `[17,512,841478,65537]`, `--probes 6 --script-debug --line-telemetry`, deux bras OpexAI `mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1`, variante `rail_depot_signal=1`, AAA rail seul avec `disable_veh_roadveh=1`, `disable_veh_tram=1`, `disable_veh_ship=1`, `disable_veh_aircraft=1`. Aucun verdict économique sur le seul smoke ; vérifier `RAIL_DEPOT_SIGNAL phase=build/upgrade`, dépôts physiques côté B, signaux PBS, erreurs moteur/Squirrel, trains bloqués et profit réel.
- Gate A, **si exposition physique + smoke sain** : `gain_short`, 40 graines canoniques × 5 ans (`--min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 5 --years 5 --line-telemetry`). Critère de gain qualifié : Δ moyen ≥4 % de la référence, Wilcoxon bilatéral p<0,05, borne basse IC95>0, 40/40 sains. Décision utilisateur supplémentaire : **si Δ moyen ≥0**, lancer B même si A non qualifiée, sans décrire cela comme une qualification A.
- Gate B conditionnelle : `non_erosion`, 20 graines × 10 ans **rail seul**, puis 20 graines × 10 ans **multimodal** (aucun `mode_*=0` ni options AAA désactivant des modes) ; à ne pas lancer si Δ moyen A négatif ou si santé/exposition non démontrée. Un seul Docker à la fois, limite **10 CPU, 8 Go RAM, 10 workers**, Docker Desktop jamais arrêté/redémarré.
- Aucun choix a posteriori de graines, d'horizon ou de seuil. Les résultats des duels restent distincts de la mesure des 180 sauvegardes SOLO historiques.

## 1. Mesure initiale, sans nouvelle partie

Sources : `results/captures_sites_rail_20261103/archives` (**180 sauvegardes**, 60 par graine 17, 512, 841478, 1970–1974) et les 3 journaux `logs/engine_seed*_pid*.log`. Décodeur documenté et fichiers CSV/JSON dans `results/rail_depot_signal_20261103/` (`analyser_sauvegardes.py`, `summary.json`, `lines.csv`, `trains.csv`, `train_history.csv`, `depots.csv`, `signals.csv`, `snapshots.csv`, `rail_builds.csv`). Lecture de la carte depuis les couches RIFF MAPT/MAPO/MAP2/M3LO/M3HI/MAP5 avec garde de taille. **Pas de nouvelle partie pour cette mesure**.

| Périmètre des sauvegardes | Valeur constatée |
|---|---:|
| Instantanés mensuels des lignes avec trains/ordres lisibles | 4 655 |
| Instantanés de trains (locomotives) | 5 157 |
| Dépôts observés sur les 180 sauvegardes | 5 158, dont 5 158 sorties localement compatibles avec une voie |
| Lignes avec dépôt ≤2 cases Manhattan d'au moins un quai | 4 403 / 4 655, **94,6 %** |
| Lignes sans signal sur une tuile à ≤8 cases Manhattan des quais | 4 153 / 4 655, **89,2 %** |
| Observations de trains « lost » | 35 |
| Observations de trains en panne | 94 |
| Observations de trains au dépôt | 112 |
| Lignes avec au moins un train lost/en panne/au dépôt | 231 / 4 655, **5,0 %** |
| Signaux, somme sur les 180 sauvegardes | **1 579 PBS**, 0 signal bloc |
| Signaux physiques aux trois dernières dates (1974-12-01) | **57 PBS**, 0 signal bloc (26, 9 et 22 par graine) |
| Lignes à profit annuel *en cours* ≤0 dans tous les snapshots | **539 / 4 655** |

**Attention aux unités :** ces 4 655 « lignes » sont des observations répétées chaque mois, pas 4 655 lignes distinctes. La ligne est reconstruite par ses ordres/stations et non par son identifiant interne OpexAI ; un dépôt proche de deux quais n'est pas forcément celui de cette ligne. La distance gare–dépôt est la Manhattan minimale au rectangle des quais, **pas** la longueur de voie jusqu'au dépôt. Un signal à huit cases n'est pas forcément sur le trajet ni orienté correctement. `profit_this_year` est le cumul YTD des véhicules encore présents, pas leur revenu annuel clos ni une perte causale démontrée. Les vitesses observées sont instantanées et les états au dépôt/à quai sont des photographies mensuelles, pas des durées. Le code de la version de référence est susceptible de comporter des trains perdus et/ou immobiles indépendamment de la signalisation.

### Association descriptive entre incidents, signaux et profit (tous checkpoints)

| Sous-groupe | Instantanés de lignes | Profit `profit_this_year` moyen, £ YTD | YTD non positif |
|---|---:|---:|---:|
| Aucun signal à proximité ≤8 cases | 4 153 | 20 971 | 539 |
| Au moins un signal à proximité | 502 | 31 510 | 0 |
| Dépôt à ≤2 cases d'un quai | 4 403 | 22 349 | 517 |
| Pas de dépôt à ≤2 cases | 252 | 17 887 | 22 |
| Train lost/panne/dépôt observé | 231 | 15 353 | 91 |
| Aucun de ces états observé | 4 424 | 22 460 | 448 |

**Ces écarts ne sont pas des pertes de profit imputables causalement** : les âges, longueurs, capacités, années, gares et appartenances diffèrent, et les mêmes lignes sont répétées. L'association sans signal/moins de profit motive un test apparié, pas un bénéfice attendu chiffré.

### Exemple de panne persistante

La graine **512** présente une locomotive identifiée **89**, suivie sur **35 checkpoints depuis février 1972**, dont l'état « PathfinderLost » apparaît **33 fois, pour la première fois au 1er avril 1972** (absent aux clichés de février et mars) : la ligne des stations `40,41` affiche un profit YTD **−2 315,82 £** en décembre 1974, sans signal trouvé à moins de huit cases des quais. Ce fait prouve une perte propre localisée, mais ne prouve pas que l'absence de PBS est la cause du `lost` ; un aiguillage incompatible ou un ordre non routable est aussi possible. Deux autres lignes réellement déficitaires à cette date : train **64**, seed 512 (au dépôt **24/41** checkpoints, gare de destination à **19 cases** du dépôt le plus proche), et train **48**, seed 841478 (au dépôt **31/52** checkpoints, gare de destination à **34 cases** du dépôt le plus proche), les deux à **−2 315,82 £** YTD ; voir `results/rail_depot_signal_20261103/rapport.md` pour les preuves et durées d'observation.

## 2. Correctif candidat

### Audit de référence AAAHogEx (lecture seule, GPL ; principes uniquement)

`ai/AAAHogEx-115/railbuilder.nut`, fonction `BuildDepotForRail` (~lignes 533–570) examine des fenêtres de cinq cases de tracé, déporte le dépôt hors des cases de voie principales et exige un raccordement dans les deux sens via `HgTile.BuildDepot`; `ai/AAAHogEx-115/tile.nut` (~771–797) teste explicitement les liaisons avec les deux voisins. Les raccordements `BuildRailloadPoints` (~394–427) ont une gestion dédiée des signaux PBS unidirectionnels aux jonctions à sens connu. Aucun code de cette IA n'a été copié : OpexAI réutilise **son propre** constructeur validant les deux liens, et conserve le PBS bidirectionnel pour sa voie simple non fléchée.

Module `ai/OpexAI/rail_depot_signal.nut` : (1) placement du dépôt de départ sur embranchement entre 4 et 12 pas le long de la voie, avec repli au dépôt historique si aucun emplacement sain, en réutilisant **`OpexBuildDepot`** et ses vérifications de raccordement ; (2) tentative d'un dépôt à l'extrémité B après démarrage réussi du train, donc non bloquante pour l'existence de la ligne ; (3) dépôt B également sur la voie secondaire indépendante quand elle existe ; (4) **PBS bidirectionnel** sur l'approche simple d'un quai joint via `OpexC41BuildPbsAtApproach`, et sur les approches de lignes partageant déjà le StationID, sans remplacer les signaux existants et sans pose unidirectionnelle dangereuse sur voie unique ; (5) traçage `RAIL_DEPOT_SIGNAL` sous `DECISION_LOG` avec tuiles de dépôt, positions sur voie, statuts PBS, refus et gares partagées ; (6) métadonnées simples de dépôt B persistées avec les lignes par la sérialisation existante.

**Limite choisie :** pas de nouveaux signaux bloc sur voie simple bidirectionnelle, afin de ne pas créer un sens interdit permanent. Les boucles V181/V199 gardent leur signalisation à sens unique existante. Pas de déplacement destructif des dépôts déjà servis, pas de destruction du quai ni de modification d'AAAHogEx. Les critères de succès sont **circulation physique et profit Opex**, non la simple construction d'un signal.

## 3. Tests et bancs

### Avant la modification

Suite complète : **3 167 tests**, 1 échec déjà présent `test_current_policy_is_observed_not_changed`, 6 skips, 2 échecs attendus. Le fichier `/openttd-ml/base_fail.txt` contient les échecs autorisés historiques. Journal `results/rail_depot_signal_20261103/baseline_unittest.txt`.

### Après la modification

- **Dernière version : onze contrats RAIL-DEPOT-SIGNAL, 11/11 OK**, dont projection SHA-256 exacte des six fichiers pré-intervention, idempotence et rejet d'un hunk partiellement modifié, absence de signaux unidirectionnels, embranchement de dégagement, PBS sur les trois voies en amont, rollback, dépôts intermédiaires et lecture des réglages réels de révision sans les modifier ; `sweeps/test_rail_depot_signal_contracts.py`. Ce sont des **tests Python de source**, pas une compilation ni une circulation Squirrel.
- **Dernière suite complète : 3 178 tests**, 1 échec `test_current_policy_is_observed_not_changed` **identique à la référence pré-intervention**, 6 ignorés, 2 échecs attendus ; **0 nouvel échec**. Fichier `results/rail_depot_signal_20261103/final_100tiles_spur_unittest.txt` (instantanés précédents conservés dans `after_v3_unittest.txt`, `reprise_after_guard_unittest_20261103.txt`, `after_100tiles_rollback_unittest.txt` et `after_route_distance_unittest.txt`). Les anciens hashes historiques et les projections RAIL-OPEN/SIBLING/V190 sont préservés.
- **`git diff --check` : OK** à la reprise. Les anciens fichiers sales non liés à cette étude restent conservés.

### Blocage au lancement du smoke — aucune partie RAIL-DEPOT-SIGNAL n'a commencé

Précondition vérifiée avant lancement : `docker ps` vide. La campagne préenregistrée **`rds_smoke_4x6_20261103`** a été soumise à `sweeps/run_c66_reference.py` avec tous les paramètres ci-dessus, `--cpus 10 --memory 8g --max-workers 10`, mais le client `docker run` est resté sans progression **sans aucun conteneur créé ni partie, sauvegarde, journal moteur ou métrique**. Une vérification des processus Windows a révélé un **autre lanceur V190-FIX** `v190_fix_independent_4x6_20261103` démarré le **03/11/2026 à 09:01:09** (client Docker PID **22692**), lui-même bloqué et toujours actif au moment du contrôle. Le client de notre smoke (PID **36456**, démarré **10:36:25**) a été interrompu **seul** après avoir constaté `docker container ls -a` vide ; ni ce lancement externe, ni le daemon/les processus Docker Desktop n'ont été arrêtés ou redémarrés. `docker info` reste opérationnel, version serveur 29.8.2, **0 conteneur exécuté**. Sortie de notre lanceur : `SMOKE_EXIT=-1`, `smoke_console.txt` ; aucune compilation/mise en mouvement du nouveau code n'a donc été observée sur OpenTTD.

| Épreuve | Santé/exposition | Δ Opex ON−OFF | V/D/E | p | IC95 | Profit Opex/AAA OFF et ON | Verdict |
|---|---|---|---|---|---|---|---|
| Smoke rail 4×6, graines 17/512/841478/65537 | **Non lancée dans le moteur**, pas d'observation de dépôts/signaux | N/D | N/D | N/D | N/D | N/D | **Bloqué avant moteur** |
| Porte A rail 40×5 | Non démarrée : smoke sans exposition ni santé vérifiées | N/D | N/D | N/D | N/D | N/D | **Non évaluable** |
| Porte B rail 20×10 | Non démarrée : Δ≥0 de A inconnu | N/D | N/D | N/D | N/D | N/D | **Non admissible** |
| Porte B multimodal 20×10 | Non démarrée : gate A non mesurée | N/D | N/D | N/D | N/D | N/D | **Non admissible** |

**Interdiction d'inférer un succès** à partir des seules observations SOLO ou des tests de source. Les étapes qui restent nécessaires : libération fiable du lancement Docker concurrent, smoke réel ON/OFF avec journaux et observations physiques, puis A et B conditionnelles comme pré-enregistré. La tâche est partiellement réalisée ; les objectifs de profit ne sont pas démontrés.

## 4. Reprise : état Docker confirmé et protection des voies (3 novembre 2026)

Après le premier rapport, un nouveau contrôle **en lecture seule** a établi que `docker desktop status` renvoie explicitement **`stopping`** et que `wsl --list --verbose` indique **`docker-desktop` à l'état `Stopped`**. Le journal `Docker/log/vm/init.log` documente un arrêt gracieux de `dockerd` et la mise hors tension de la VM autour de **09:00 heure de Paris**. Un `docker system df` de diagnostic est resté bloqué et **seul ce client de diagnostic**, formellement identifié comme appartenant à cette reprise (PID 16568), a été arrêté. Des clients de sondage externes `docker run alpine` et `docker events` étaient également encore présents. Le client V190-FIX **PID 22692** et ses parents sont restés intacts, de même que tous les processus de Docker Desktop. Aucun `docker stop`, redémarrage, arrêt de Docker Desktop ou nouvelle simulation n'a été fait. La coexistence des clients bloqués ne suffit pas à prouver qu'ils ont causé l'arrêt du moteur.

**Correctif de sûreté supplémentaire, uniquement dans le nouveau module opt-in :** le dépôt B (et les dépôts proches du départ) ne propose plus au constructeur historique les cases occupées par une voie ferrée préexistante dans les neuf fenêtres sondées ; sur une double voie, chaque dépôt terminal interdit explicitement le tracé de l'autre voie, ses dépôts connus et le dépôt B nouvellement placé. Cette précaution évite de proposer à `OpexBuildDepot` des cases dont la démolition pourrait toucher une voie indépendante RAIL-PAIR/V190-FIX. Elle ne démontre ni construction effective ni absence d'autres interactions en moteur : **validation OpenTTD toujours requise**.

Après cette garde : **8/8 contrats dédiés**, **3 175 tests complets avec l'unique échec de référence déjà présent** et `git diff --check` OK. Projection historique OFF des six fichiers **inchangée et exacte**. Les résultats des portes A et B restent **N/D**, et les exigences de maintenance effectivement utilisée côté B et de signalisation sûre des longs tronçons multi-trains restent **non vérifiées / partiellement implémentées**. Le blocage `stopping` ne peut être levé dans cette étude sans enfreindre l'interdiction explicite de redémarrer Docker Desktop ; aucun banc supplémentaire n'est lancé dans cet état.

## 5. Complément utilisateur — espacement ~100 tuiles, embranchements et révisions (3 novembre 2026)

**Nouvelle spécification ajoutée après le premier correctif :** les dépôts ne doivent plus être collés à la sortie des gares ; viser environ un dépôt tous les 100 carreaux sur les longues lignes, sur un embranchement suffisamment long pour garer une rame complète sans engager l'aiguillage. Poser trois signaux **PBS normaux bidirectionnels** avant la jonction du dépôt : un sur chacune des deux approches de la voie principale et un sur la branche de sortie du dépôt, **jamais immédiatement après l'aiguillage**. L'enjeu est la circulation et l'entretien réellement rendus, pas le nombre brut de dépôts.

### Mesures complémentaires sur les 180 sauvegardes SOLO, sans nouvelle partie

- Les **180/180** sauvegardes contiennent `difficulty.vehicle_breakdowns = 1` : pannes **actives en fréquence réduite** dans ces parties historiques (`0` désactive, `1` réduit, `2` est normal). Le réglage `order.no_servicing_if_no_breakdowns = 1` est lui aussi présent, mais ne désactive pas les révisions puisque les pannes sont activées. Le harnais SOLO hérite de cette configuration ; vérifier le PATS des futurs duels, sans présumer qu'une propriété non explicitement forcée est identique dans tous les environnements.
- Les **180/180** sauvegardes conservent aussi les réglages effectifs de compagnie sous `PLYR['0']['settings'][0]` : **`settings.vehicle.servint_ispercent=0`** et **`settings.vehicle.servint_trains=150`**. Les **5 157/5 157** observations de locomotives ont `service_interval=150`. L'intervalle est donc bien de **150 jours et non de 150 % de fiabilité**. **94** observations ont `breakdown_ctr > 0`, **603** ont un compteur `breakdowns_since_last_service>0`, et **961/5 157** montrent plus de **150 jours depuis la dernière révision**, soit un dépassement réel de l'intervalle déclaré à ces checkpoints. Ce sont des observations mensuelles répétées, non 94 pannes distinctes ni 961 trains distincts.
- **45** photographies mensuelles ont un ordre courant de type `GOTO_DEPOT` dont la cible est reconnue comme dépôt ; la distance de Manhattan encore restante au dépôt est médiane **1 tuile**, maximum **5**. Le journal des ordres permanents ORDL ne comporte **aucun ordre explicite de dépôt**. Ces données n'estiment **pas** le détour total subi par le train, encore moins le temps de maintenance cumulé, puisque les positions ne sont échantillonnées qu'une fois par mois.
- Les traces A* réussies appariées aux 124 constructions finales comptent **68/124** longueurs de tracé `routeLen > 100` : graine 17 **22/41**, 512 **16/40**, 841478 **30/43**. Cette mesure est un motif concret pour des dépôts intermédiaires. Dans 36 mois avec une seule ligne longue construite, l'écart de nombre de dépôts entre sauvegardes a été +1 dans 30 cas, +2 dans 4, nul dans 1, +3 dans 1. **Dans les 30 mois avec exactement un nouveau dépôt**, celui-ci se situe à **3–13 tuiles** de la cible cargo d'origine (médiane **7**) contre **100–187 tuiles** de celle d'arrivée (médiane **134**) : un signal fort de concentration à l'origine, mais attribution temporelle, **pas preuve de l'itinéraire exact ni de causalité**.
- Les trois trains finaux déficitaires 89 (seed 512), 64 (seed 512), 48 (seed 841478) n'ont ni panne en cours ni retard de révision de plus de 150 jours dans les clichés de leur histoire. Leur service est daté régulièrement ; cela peut traduire un séjour très long en dépôt, et ne prouve **pas** des passages fréquents indépendants. La perte de profit observée ne saurait donc être attribuée sans preuve à une panne ou à l'absence de dépôt.

### Nouveau correctif opt-in développé, non exécuté en moteur

Dans `rail_depot_signal.nut`, `OpexRailDepotSignalTrySpur` remplace la simple insertion du bâtiment juste à côté du chemin : il cherche une tuile d'aiguillage **hors gorge**, exige deux approches principales sans autre aiguillage dans la zone de dégagement et un terrain **libre** pour construire une branche droite de `2 × platformLength + 2` cases et son dépôt. Un PBS sortant est placé au milieu de la branche, à plus d'une longueur de rame du dépôt et de la jonction ; deux PBS supplémentaires sont posés sur les voies principales avant l'aiguillage à une distance `platformLength + 2` tuiles. Il n'ajoute jamais de `SIGNALTYPE_PBS_ONEWAY`. La valeur **réelle prévue du quai** `candidate.platformLength` ou `line.platformLength` est propagée aux cinq appels de dépôt primaire et à l'upgrade ; le constructeur refuse l'implantation si les conditions ne sont pas réunies et **ne revient plus au dépôt en gorge** sous ce réglage. Cette politique plus stricte peut réduire les constructions : elle devra impérativement être validée en smoke avant qualification.

Les lignes de plus de 100 tuiles de chemin **mesurées par la somme des Manhattan entre éléments du parcours (ponts/tunnels compris)** sont partagées en sections de longueur voisine de 100 : chaque section intérieure fait l'objet d'une recherche locale de dépôt intermédiaire, sans annuler la ligne si aucun site ne convient. Les nouvelles implantations produisent `RAIL_DEPOT_SIGNAL phase=spur` (jonction, longueur, trois PBS), `phase=coverage` (longueur et dépôts intermédiaires posés) et `phase=config` (valeurs effectives `difficulty.vehicle_breakdowns`, `vehicle.servint_trains`, `vehicle.servint_ispercent`, avec `AIGameSettings.IsValid` avant toute lecture) sous `DECISION_LOG`. Aucun ordre de révision explicite n'est injecté : il reste à mesurer que l'algorithme automatique d'entretien emprunte effectivement ces installations et ne provoque pas de `PathfinderLost`. Une fonction de rollback spécifique retire les voies d'embranchement et signaux posés lorsqu'une construction primaire échoue ; elle est appelée **uniquement sous le flag RDS**, après vente des véhicules arrêtable et avant le rollback historique.

**Garantie OFF :** les SHA-256 pré-intervention des six fichiers historiques et le fichier `sweeps/fixtures/rail_depot_signal_off.json` restent **inchangés**. Le projecteur `rail_depot_signal_legacy.py` retire de manière explicite les arguments de longueur ajoutés aux hunks RDS et la garde de rollback, avant d'appliquer la fixture historique. Les contrats dédiés vérifient cette reconstruction exacte. Le dépôt et ses signaux sont **candidats techniques**, pas une topologie confirmée par OpenTTD ; ce sont uniquement des contrats de source tant que le moteur n'a pas démarré une partie RDS.

**État de la validation économique :** smoke, porte A, portes B et ratios Opex/AAA **N/D**. Aucun chiffre de gain n'est attribué à ces nouvelles règles avant circulation et transport rémunéré vérifiés en moteur. L'état Docker/WSL et les processus V190-FIX doivent rester réconciliés avant tout nouveau lancement.

### Dernier contrôle opérationnel

Au dernier contrôle après le complément, `docker desktop status` affiche **`starting`** (session différente de l'ancien `stopping`) **sans aucune action de redémarrage par cet agent**. Les anciens processus `docker run` et Python de la campagne V190-FIX ne figurent plus parmi les processus filtrés, mais `docker ps` s'est bloqué tant que le démarrage n'était pas achevé ; seul le client de lecture **propre à cette reprise** a été arrêté après identification. **Il n'existe toujours aucune confirmation que Docker accepte de créer un conteneur ni que le moteur OpenTTD a chargé le correctif.** Aucune nouvelle campagne RDS n'a été lancée. Branche `exp/rail-sibling-20261102`, HEAD `99f29d9c858f390de6193978a4f12d3fbdb48127`, `git diff --check` OK, aucun commit/push/merge/stash/reset/clean. Dernière suite **3 178 tests, 1 seul échec de référence antérieur**, aucun nouvel échec. Prochaine action opérationnelle admissible : vérifier `docker desktop status=running`, `docker ps` *et* l'absence de clients concurrents avant le smoke 4×6, puis décider de Gate A/B selon les critères pré-enregistrés, sans redémarrer Docker Desktop.

## 6. Revue supplémentaire du constructeur et blocage moteur documenté (3 novembre, reprise)

La reprise a confirmé la **syntaxe attendue des API NoAI** `AIRail.BuildRail`, `AIRail.AreTilesConnected`, `AIRail.BuildRailDepot`, `AIRail.BuildSignal`, `AIRail.GetSignalType`, `AIRail.RemoveRail` et `AIGameSettings.IsValid/GetValue` au moyen de leur documentation. **Cette vérification d'API n'est pas une compilation Squirrel réelle.** L'implémentation opt-in a été renforcée de trois manières :

1. **Raccordement accessible des deux côtés :** chaque embranchement construit une courbe depuis le côté amont et une depuis le côté aval, puis vérifie `AreTilesConnected` pour l'accès dépôt depuis les deux sens **et** la continuité de la voie commerciale. En cas d'échec, les courbes ajoutées sont retirées sans toucher à la voie historique. Les extrémités de pont/tunnel éloignées de plus d'une tuile sont refusées avant tout appel dont la précondition exige l'adjacence.
2. **Aucun signal parasite dans le dégagement :** toute présence d'un signal existant sur la zone prévue pour une rame entière provoque le refus de l'embranchement. À l'extension d'une seconde voie, `OpexPlaceJoinSignals` ne repasse plus sous l'opt-in immédiatement après que le dépôt RDS a reçu ses trois PBS ; le mode OFF appelle toujours exactement la routine historique. Le rollback de l'embranchement retire les deux courbes, les nouvelles voies latérales et les trois signaux effectivement posés.
3. **Diagnostic d'exposition :** `RAIL_DEPOT_SIGNAL phase=primary` journalise les refus `NO_SAFE_SPUR` ; `phase=intermediate_skip` marque les emplacements intermédiaires non constructibles ; `phase=coverage` donne le nombre de cibles et de dépôts réellement posés. Ces logs permettent de différencier un manque de sites du défaut de circulation lors du futur smoke.

Le projecteur `sweeps/rail_depot_signal_legacy.py` retire **uniquement** ces nouveaux ajouts opt-in, notamment la neutralisation de l'ancien appel de signaux en expansion, avant de vérifier les SHA-256 pré-intervention **inchangés**. Dernières validations de cette reprise : **11/11 contrats dédiés OK**, `git diff --check` OK et **3 178 tests complets**, avec l'unique échec de référence déjà présent `test_current_policy_is_observed_not_changed`, 6 skips et 2 expected failures ; aucune nouvelle défaillance (`results/rail_depot_signal_20261103/reprise_bidirectional_signal_unittest.txt`). Aucun commit, push, merge, stash, reset ni nettoyage.

**Cause opérationnelle beaucoup mieux identifiée :** `docker ps` renvoie maintenant explicitement `Docker Desktop is unable to start`. Le journal `com.docker.backend.exe.log`, vers 11:35 heure locale, indique : `service containerd failed: panic detected in containerd: panic: invalid page type: 61: 10`, avec une pile `go.etcd.io/bbolt`. Les journaux de VM montrent ensuite un arrêt explicite du daemon et l'extinction de la VM. Cela confirme un **échec interne au démarrage de containerd**, compatible avec un problème de base de métadonnées bbolt mais ne prouvant ni son emplacement ni une réparation particulière. **Aucune suppression/réparation de données Docker, réinitialisation ou redémarrage Docker Desktop** n'a été tentée, conformément à l'interdiction utilisateur. Les anciens clients V190-FIX n'étaient plus présents au dernier contrôle. Le smoke et toutes les portes économiques restent **N/D** : il serait incorrect de qualifier l'amélioration physique ou le profit sans aucune simulation RDS.

**Prochaine étape bloquée :** retrouver un moteur Docker opérationnel sans intervention contraire à la consigne, vérifier `docker ps` vide et aucun client concurrent, puis lancer le smoke RDS 4×6 exactement comme pré-enregistré. Gate A et les deux B ne sont admissibles qu'après les résultats physiques et statistiques requis. Le présent livrable clôt la **documentation de la reprise**, pas la qualification économique.

## 7. Reprise sur Docker Desktop reconstruit — 3 novembre 2026, après 11 h 53

**Runtime de nouveau joignable :** `docker desktop status=running`, contexte `desktop-linux`, serveur `29.8.2`, image locale `openttd-lab:latest` (`sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`). Le premier lancement du smoke `rds_smoke_4x6_20261103` a échoué avec le code Docker **125 avant création du conteneur**, car le montage direct du worktree Windows a été refusé : `path ... .wt_sibling_20261102 is not shared from the host`. Aucun résultat `.json/.jsonl`, sauvegarde ou journal de simulation n'a été créé par cet essai. Il ne s'agit **pas** d'une défaillance de l'IA.

Un diagnostic de montage sans simulation a confirmé qu'un montage en lecture seule du dossier parent `C:\Users\jr\vscode\openttd-ml\openttd-ml` fonctionne et permet de voir `.wt_sibling_20261102/sweeps/run_c66_reference.py` dans le conteneur. Le lanceur accepte `--mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml'`, ce qui conserve le worktree comme répertoire d'exécution et les archives sous son `results/`. Aucun réglage ou redémarrage Docker Desktop/WSL n'a été fait.

La reprise avec ce montage a été **refusée avant démarrage** par la garde imposée `docker ps` vide : plusieurs conteneurs actifs d'un autre environnement, nommés `fr-ordres-atelier-imperatif__*__env-main-1` et leurs sidecars, sont apparus entre les contrôles. Une attente bornée d'environ 30 secondes n'a trouvé aucun créneau vide ; ces conteneurs tiers sont restés intacts. **Le smoke RDS 4×6 n'a donc toujours produit aucune partie**, et ses portes A/B demeurent conditionnellement bloquées ; Δ profit, V/D, Wilcoxon p, IC95, ratios Opex/AAA, dépôts réellement posés, `NO_SAFE_SPUR`, trains circulants et profit par train sont **N/D**, sans extrapolation des résultats historiques.

Contrôles Python de cette reprise : `test_rail_depot_signal_contracts.py` **11/11 OK**, contrats V190-FIX **5/5** et directionnalité **9/9 OK** ; suite globale **3 187 tests**, **un seul échec préexistant** `test_current_policy_is_observed_not_changed`, 6 ignorés, 2 échecs attendus ; `git diff --check` OK. Aucun défaut, commit, stash, reset, fusion ou publication modifié. La commande du smoke conserve les quatre graines `17 512 841478 65537`, `--years 6 --probes 6 --script-debug --line-telemetry --retain-savegames results/rds_smoke_4x6_20261103_saves`, les bras RDS OFF/ON, les quatre désactivations AAA, `--value-guard-max-loss-pct 100`, `--cpus 10 --memory 8g --max-workers 10`, et ajoute uniquement le `--mount-root` confirmé. **Ne relancer qu'après `docker ps` vide.**

RAIL-DEPOT-SIGNAL TERMINÉ

## Reprise opérationnelle du 3 novembre, après reconstruction Docker

Docker répond de nouveau, mais la précondition explicite du nouveau protocole (`docker ps` vide avant chaque banc) n'est pas satisfaite : quatre conteneurs étrangers à OpenTTD sont actifs, deux `env-main` et deux `harbor-docker-egress-control-sidecar`, sous les préfixes `fr-ordres-atelier-imperatif__yl2hu7e` et `fr-ordres-atelier-imperatif__xdm6kjw`. Aucun n'a été arrêté. En conséquence, le smoke `rds_smoke_4x6_20261103` n'a pas été lancé à cette reprise ; exposition, santé, Δ, V/D, p, IC95 et ratios restent N/D. Les portes conditionnelles restent en attente de ce smoke.

## 8. Bancs moteur exécutés après précision Harbor (3 novembre 2026)

**Cette section actualise les constats devenus obsolètes des §§3–7** : l'utilisateur a précisé que les conteneurs `fr-ordres-atelier-imperatif__*` sont le travail Harbor indépendant et doivent rester intacts. Le contrôle d'exclusivité vise seulement `openttd-lab`. Le harnais a été relancé dans le worktree avec `--mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml'`, **`--cpus 9 --memory 8g --max-workers 9`**, `--value-guard-max-loss-pct 100`, les quatre désactivations des véhicules AAA hors rail, `--probes 6 --script-debug --line-telemetry --line-telemetry-monthly --retain-savegames`, graines **17 512 841478 65537**, six années 1970–1975. Aucun conteneur OpenTTD n'a été lancé en parallèle d'un autre ; Docker Desktop/WSL et Harbor sont restés intacts.

| Mesure 4×6, 8/8 duels complets | RDS initial | RDS après correction expérimentale |
|---|---:|---:|
| Campagne et JSON | `results/rds_smoke_4x6_20261103.json` | `results/rds_smoke_orientation_4x6_20261103.json` |
| Bundle figé SHA256 | `dab0c9a367f2a3e9afddf8481147d7138ee3e45c4124916691666e479e2d7ef3` | `db0e0d803fa0112575386cabe04da45f7d1a5529e60e5171cb4fadb168b40dee` |
| Δ moyen `profit_year` ON−OFF | **−1 306 552,25 £/an** | **−935 033,50 £/an** |
| V/D/E ; Wilcoxon bilatéral | **0/4/0 ; p=0,125** | **0/4/0 ; p=0,125** |
| IC95 bootstrap du Δ | [−1 671 765,75 ; −1 028 026] £ | [−1 084 146 ; −785 921] £ |
| Ratio des valeurs de compagnie ON/OFF | **10,25 %** | **32,33 %** |
| Ratio des profits moyens Opex ON / AAA ON | **5,06 %** | **21,03 %** |
| Trains Opex ON terminaux dans 4 graines | 55 | 124 |
| Trains `PathfinderLost` ON / OFF sur saves finales | **24/55 contre 1/201** | **26/124 contre 2/202** |
| Lignes construites ON / OFF (logs) | **57 / 176** | **121 / 177** |
| Verdict du harnais | `fail_primary` | `fail_primary` |

Les journaux moteur sont sous `results/<campagne>_engine/` et les sauvegardes sous `results/<campagne>_saves/`. Les 8/8 jeux de chaque campagne ont atteint l'horizon, sans erreur de script fatale, mais **le smoke est physiquement malsain** : le décodage des cartes, dépôts et locomotives des sauvegardes finales établit que **toutes les 24 puis 26 locomotives `PathfinderLost` du bras ON se trouvent sur les embranchements de dépôt ajoutés par RDS**. Le repli de construction `NO_SAFE_SPUR`/`DEPFAIL` réduit également le portefeuille de lignes. Une première correction expérimentale dans `rail_depot_signal.nut` a inversé les trois `front` des signaux PBS selon l'approche des trains (`spurFront = branch[l + 1]`, `tiles[at - step]`) et élargi de 12 à 100 le balayage des sites hors gorge, sans changer le défaut du réglage. Elle améliore le volume de constructions, **mais ne rétablit pas les trajets des trains**. Aucun gain économique n'est attribuable à ce correctif.

**Décision : porte A rail 40×5 et les deux portes B rail/multimodal 20×10 refusées tant qu'un smoke sans locomotives perdues sur les embranchements n'est pas obtenu.** Les résultats de ces portes restent non mesurés, pas nuls. Contrats RDS **11/11**, V190 **5/5**, directionnel **11/11** ; suite complète de reprise **3 189 tests**, un unique échec historique `test_current_policy_is_observed_not_changed`, 6 ignorés, 2 échecs attendus ; `git diff --check` OK. Aucun commit, push, merge, stash, reset ou changement de défaut.

## 9. Autopsie causale, garde fail-closed et bancs achevés (3 novembre, dernier état)

### 9.1 Preuves physiques dans les sauvegardes RDS

Le smoke `rds_smoke_orientation_4x6_20261103`, bundle `db0e0d803fa0112575386cabe04da45f7d1a5529e60e5171cb4fadb168b40dee`, a perdu **26/124 trains ON** contre **2/202 OFF** à décembre 1975. Les 26/26 rames ON perdues sont sur les branches RDS, et 147 tentatives `DEPFAIL` ont été observées. Δ moyen ON−OFF **−935 033,50 £/an**, 0V/4D, p=0,125, IC95 [−1 084 146 ; −785 921] £. L'inversion du `front` et le balayage porté à 100 sites étaient déjà présents : ils n'ont pas réparé le trafic.

La locomotive **182** seed17, gares **41↔42**, dépôt 51415, jonction 51406, est perdue dans **53/53 sauvegardes mensuelles** (1971-07 à 1975-12), oscille entre embranchement et dépôt et n'a jamais visité de gare ; −2 315,82 £ YTD à fin 1975. Le décodeur `results/rail_depot_signal_20261103/analyser_sauvegardes.py`, `VEHS`/`ORDL`/`STNN` et les couches RIFF `MAP5`/`MAP2` montrent une voie et des ordres **statiquement continus** vers les gares 41 et 42, mais une réservation qui **ne dépasse pas la jonction** vers la première gare. Cette observation n'identifie pas à elle seule l'instruction YAPF fautive.

Quatre ablations **temporaires**, chacune limitée au dépôt **51415** sur la seed17 et suivie d'une restauration du code, ont discriminé la contribution de la signalisation. Les jeux 1×3 ont tous terminé 2/2 duels :

| Campagne `results/<id>.json` | Signaux supprimés uniquement au dépôt 51415 | Sortie de l'embranchement au dernier checkpoint | Δ compagnie ON−OFF à 3 ans |
|---|---|---|---:|
| `rds_probe_spurpbs_seed17_1x3_20261103` | PBS branche uniquement | Véhicule 176 perdu, gare jamais visitée, −2 323 £ YTD | −521 904 £ |
| `rds_probe_mainpbs_seed17_1x3_20261103` | Deux PBS de voie principale | Véhicule 225 perdu, gare jamais visitée, −2 323 £ YTD | −475 659 £ |
| `rds_probe_main_a_only_seed17_1x3_20261103` | PBS branche + un PBS principal (A conservé) | Véhicule 225 perdu, gare jamais visitée, −2 323 £ YTD | −473 332 £ |
| `rds_probe_allpbs_seed17_1x3_20261103` | Les trois PBS autour de la branche | Véhicule 198 sort, visite 41 et 42, `PathfinderLost` disparaît, **+14 414 £ YTD** en 1972 | −488 000 £ |

Les quatre bundles sont **distincts** : les Δ de compagnie ne constituent **pas** des différences appariées entre les ablations ; leur preuve est la trajectoire décodée. Le véhicule 198 était encore `PathfinderLost` au premier instantané après sa mise en service, puis s'est **récupéré**. Les PBS peuvent donc empêcher sa récupération sans être forcément la cause initiale du défaut. La suppression générale des PBS n'est **pas une politique de signalisation sûre** pour une ligne à plusieurs trains et n'a pas été conservée.

Une tentative de deux faces PBS sur une même tuile, `rds_twoface_fallback_diag_1x3_20261103`, bundle `6bb026dc9c92c9db300f281fe5febbfe57a8779ee30c2431d8b393de3cb75b11`, a produit **0 spur**, 10 replis historiques et Δ −720 966 £ : OpenTTD ne propose pas de signal `PBS_TWOWAY` analogue aux signaux de bloc, et cette séquence de deux `BuildSignal` n'a pas réussi. Le patch a été **annulé**. Les jonctions `MAP5=21/26/38/41` et des empreintes identiques `(trackbits, direction, longueur rame, faces PBS)` comportent des trains **rémunérateurs et perdus** ; une whitelist/blacklist fondée sur ces seuls champs serait dangereuse. Il faut un véritable contrôle de routabilité YAPF et de première desserte avant d'exposer d'autres embranchements.

### 9.2 Correctif conservateur réellement laissé dans le worktree

- `OpexRailDepotSignalBuildPrimary(...)` tente `OpexRailDepotSignalBuildNear(...)` puis, si `null`, **`OpexBuildDepot(tiles, extraForbidden)`**. Ce repli évite qu'une simple absence de site RDS provoque systématiquement `DEPFAIL` et rollback d'une ligne autrement viable. Un échec du dépôt historique reste un vrai `LEGACY_DEPFAIL`, non masqué.
- `OpexRailDepotSignalSpurRoutingCertified()` retourne **`false`** tant qu'aucune nouvelle architecture ne prouve sa sécurité. Les branches primaires, intermédiaires et terminales RDS, ainsi que la protection de lignes anciennes, sont donc refusées **avant construction** ; `OpexRailDepotSignalEnhance` retourne les champs d'absence sans poser de signal.
- Sur le chemin d'upgrade, `builder_rail.nut` ne neutralise `OpexPlaceJoinSignals` **que si RDS est certifié**. Le fallback historique conserve ses signaux habituels. `sweeps/rail_depot_signal_legacy.py` projette toujours exactement le code OFF gelé ; les réglages opt-in gardent leur défaut **0**. La recherche 100 sites et les trois PBS normaux restent dans le module comme code inactif, sans prétendre qu'ils sont sûrs.

### 9.3 Résultats du smoke 4×6 et de la porte A 40×5 du fallback

**Même bundle** dans les deux campagnes : `c57374347c7c6089a7e220f5d783c9086e81771d1cdcaa34ffe39b41fa2b42c3`, OpenTTD 15.3, NoAI 15, OpenGFX 7.1, 256², AAA **RAIL seul**, garde de valeur `100`, `--mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml'`, `--cpus 9 --memory 8g --max-workers 9`, aucun autre banc OpenTTD simultané, Harbor préservé.

| Indicateur | Smoke `rds_failclosed_smoke_4x6_20261103` | Porte A de contrôle `rds_failclosed_A40x5_20261103` |
|---|---:|---:|
| Exécutions | **8/8** (4 graines × OFF/ON × 6 ans) | **80/80** (40 graines canoniques × OFF/ON × 5 ans) |
| Δ moyen `profit_year` ON−OFF | **+48 382,50 £/an** | **−12 257,95 £/an** |
| V/D/E | 2/0/2 | **8/10/22** |
| Wilcoxon bilatéral | p=0,5 | **p=0,468292** |
| IC95 bootstrap du Δ | [0 ; +124 500] £ | **[−35 894,675 ; +11 263,1] £** |
| Ratio des valeurs ON/OFF | 105,487 % | **97,576 %** |
| Ratio des profits moyens Opex ON/OFF | 103,163 % | **99,227 %** |
| Profit Opex propre moyen ON | 1 577 969 £/an | 1 574 070,925 £/an |
| Profit AAA moyen ON | 2 136 327,75 £/an | 1 968 666,35 £/an |
| Embranchements RDS réellement créés | **0** | **0 (garde statique)** |
| `PathfinderLost` sur sauvegardes finales Opex ON / OFF | **2 / 2** | Non mesuré : aucun `--retain-savegames` au 40×5 |
| Santé des jeux | 8/8 `complete` | 36 ON + 37 OFF `complete`, **4 ON + 3 OFF `stagnation_suspect`** |
| Décision | Pas d'exposition RDS, validation du repli uniquement | **`fail_primary`**, aucun gain ni 40/40 sains |

Fichiers sources et traces : `results/rds_failclosed_smoke_4x6_20261103.json`, `.manifest.json`, `_engine/`, `_saves/` ; `results/rds_failclosed_A40x5_20261103.json`, `.jsonl`, `.manifest.json`, `_engine/`. Le smoke a journalisé des `phase=legacy_fallback`, sans création de `phase=spur` : ne pas assimiler « peu de lost » à une nouvelle signalisation validée. Le 40×5 n'a pas besoin de sauvegardes pour son verdict **économique**, mais ne saurait démontrer la santé individuelle des locomotives.

**Décision des portes :** Gate A RDS **échouée** (Δ moyen négatif, p non significatif, aucune exposition de la variante et 7 parties `stagnation_suspect` toutes politiques confondues). Aucune Gate B 20×10 RAIL ni multimodale n'a été lancée : Δ A négatif et critère physique absent. Le smoke V190 indépendant et sa décision sont documentés séparément dans `docs/v190_fix_20261103.md` §I. La suite complète post-banc a exécuté **3 191 tests**, avec **un seul échec préexistant** `test_b6_portfolio_causality.TestB6PortfolioCausality.test_current_policy_is_observed_not_changed`, six skips et deux expected failures (`results/rds_v190_postbench_suite_20261103.txt`). `git diff --check` valide. Aucun commit/push/merge/stash/reset/clean, aucun redémarrage Docker/WSL, aucune intervention Harbor.

**Conclusion :** les nouveaux embranchements PBS RDS ne sont **pas réparés** ; seule la destruction du portefeuille par `DEPFAIL` et l'exposition aux embranchements malsains sont neutralisées. La prochaine version doit fournir une preuve de réservation sûre et de première gare atteinte **avant** de remettre `OpexRailDepotSignalSpurRoutingCertified()` à `true`. Ne pas interpréter cette protection comme une adoption du levier RDS.
