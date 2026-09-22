# Revue de code intégrale OpexAI — 2026-09-22

## 1. Périmètre, état de référence et méthode

Cette revue couvre les lots 1 à 56 du plan de revue intégrale, puis propose l'ordre de correction du lot 57. Elle est strictement diagnostique : aucun comportement OpexAI, réglage, test ou harnais n'est modifié.

État de référence vérifié avant lecture :

- dépôt : `/openttd-ml` ;
- HEAD : `de6e48e2aea0491d6b67d8efc935f1fe43a4420c` ;
- HEAD détaché sur le même commit que `master` et `origin/master` ;
- worktree initial propre ; `git diff --stat` et `git diff --check` vides ;
- `docs/taches.md` courant au 2026-09-22 est traité comme la seule liste autoritaire du travail restant (`docs/taches.md:3-12`).

Les anciennes revues ne sont pas utilisées comme backlog. En particulier, AIR capital frontier / best equipment / lifecycle expérimental post-C68 restent clos ou abandonnés (`docs/taches.md:231-260`), les flags économie/events récemment retirés ne sont pas réintroduits, C52/C60 restent clos, et C57/Lakes n'est pas rouvert comme chantier économique.

Échelle utilisée :

- **élevé** : peut laisser des actifs physiques hors inventaire, déclarer une opération réussie sans service, ou casser l'atomicité d'une transaction ;
- **moyen** : décision économique faussée, opportunité manquée, tranche non bornée ou classification d'erreur pouvant influencer le comportement ;
- **faible** : instrumentation, documentation, compatibilité ou dette de test sans effet économique direct démontré.

L'absence de finding signifie « aucun finding matériel démontré statiquement au HEAD », pas une preuve absolue d'absence de défaut runtime.

## 2. Synthèse des findings matériels

| ID | Catégorie | Gravité | Exposition | Résumé |
|---|---|---:|---|---|
| F-RAIL-ECON-01 | économie / décision | moyen | défaut | le capital rail omet le coût réel du dépôt |
| F-ROAD-TXN-01 | builder / cohérence | élevé | défaut | rollback route après démarrage partiel peut laisser un véhicule orphelin |
| F-RAIL-START-01 | builder / service | élevé | défaut | le retour de `StartStopVehicle` est ignoré sur les trains |
| F-RAIL-DEPOT-01 | builder / effet de bord | moyen | défaut | une tuile est démolie avant le probe de constructibilité du dépôt |
| F-RAIL-TXN-02 | builder / cohérence | élevé | défaut | échec du second train ignore `rollbackVehicles` |
| F-AIR-ORDER-01 | builder / ordres | élevé | défaut via croissance flotte | fallback AIR ignore l'échec de `ShareOrders` |
| F-LIFE-SCRAP-01 | lifecycle / inventaire | élevé | défaut | le scrap oublie un véhicule si `SellVehicle` échoue |
| F-AIR-ERR-01 | erreur / décision | moyen | défaut | échec HUB/HUBB peut réutiliser un `AIError` périmé |
| F-RAIL-ERR-01 | instrumentation | faible | défaut | ORDFAIL rail conserve un code d'erreur nul/ancien |
| F-C80-TOWN-01 | scheduler / opcode | moyen | C80 worker town=1 | town-growth retombe sur le chemin monolithique si un autre worker occupe le registre |
| F-C77-SLICE-01 | scheduler / opcode | moyen | C77=1 | `regen_candidates` ignore budget et deadline et saute la file de fond |
| F-EVENT-BACKLOG-01 | scheduler / opcode | faible à moyen | défaut | `_processEvents` vide toute la file sans quota avant le scheduler |
| F-C77-CARGO-01 | décision C77 | élevé sous C77 | C77=1 | le cargo fret trouvé par le rail ciblé n'est pas propagé à la route ciblée |
| F-SIGN-01 | instrumentation | faible à moyen | défaut (`debug_signs=1`) | `OpexSign` ne borne pas tous les noms à 31 caractères |
| F-TEST-01 | harnais / dette | faible | développement | deux échecs de tests historiques restent explicitement connus |
| F-DOC-DEPS-01 | dette architecturale | faible | maintenance | la doc décrit encore `lib_water.nut`/Lakes comme chemin courant alors qu'il n'est plus chargé |

## 3. Résultats lot par lot

### Lot 1 — État de référence et périmètre

**Aucun finding matériel.** HEAD, worktree, relation à `master` et décisions courantes de `docs/taches.md` ont été vérifiés avant audit.

### Lot 2 — Boot et ordre de chargement

**Aucun finding matériel.** `OpexLoadSettings()` est appelé avant la réconciliation et avant la boucle principale (`ai/OpexAI/main.nut:459-498`) ; événements puis scheduler sont exécutés à chaque tour (`:546-562`).

### Lot 3 — Déclaration des réglages

**Aucun finding matériel.** Les défauts courants reflètent les décisions du 22 septembre ; `save_full_state` vaut 1 par défaut (`ai/OpexAI/info.nut:35-41`).

### Lot 4 — Chargement des réglages

**Aucun finding matériel.** C69/C70/C75 sont lus à `ai/OpexAI/settings.nut:217-244`, C76/C77/C80 à `:333-338`. Les doublons de constantes neutres restent de la compatibilité de cadence, pas un problème fonctionnel ouvert.

### Lot 5 — État global et caches

**Aucun finding matériel.** Les caches/ledgers inspectés ont des resets ou reconstructions ; le reload reconstruit notamment les facteurs calibrés après les lignes vivantes (`ai/OpexAI/persist.nut:619-622`).

### Lot 6 — Catalogue et statique

**Aucun finding matériel.** Le coût du dépôt rail est bien collecté par le catalogue (`ai/OpexAI/catalog.nut:415-419`) ; son absence du modèle économique est traitée au lot 9.

### Lot 7 — Économie commune

**Aucun finding matériel.** Les unités et conventions communes inspectées sont cohérentes. `INFRA_AMORT_PCT=0` et `TRANSIT_COST_PERMILLE=0` sont des décisions courantes (`ai/OpexAI/settings.nut:355-356`).

### Lot 8 — Économie route

**Aucun finding matériel.** `OpexRoadLineEconomics` borne la flotte et compte route, deux arrêts et dépôt dans le capital (`ai/OpexAI/economy.nut:606-701`).

### Lot 9 — Économie rail

**F-RAIL-ECON-01 — capital rail sous-estimé du prix d'un dépôt.**

- **Fichier:ligne :** `ai/OpexAI/economy.nut:277-285`, `:319-327` ; `ai/OpexAI/catalog.nut:415-419`.
- **Trigger :** toute évaluation de candidat rail.
- **Impact :** capital, ROI et financabilité sont optimistes du coût d'un dépôt ; avec `INFRA_AMORT_PCT=0`, le profit annuel n'est pas directement gonflé, mais l'arbitrage capital/profit l'est.
- **Preuve :** le catalogue collecte `costRailDepot` ; `infraCost` rail ne contient que voie + deux quais.
- **Incertitude :** l'impact agrégé n'a pas été rejoué dans cette revue.

### Lot 10 — Économie AIR

**Aucun finding matériel.** L'économie active reste le socle C68 + calibrations courantes ; frontier/best-equipment/lifecycle expérimental ne sont pas rouverts.

### Lot 11 — Économie eau

**Aucun finding matériel.** `OpexWaterEconomics` (`ai/OpexAI/builder_water.nut:282-329`) utilise le chemin courant borné et les coûts d'infrastructure associés.

### Lot 12 — Génération générique candidats

**Aucun finding matériel.** `OpexBuildCandidates` sépare pax/fret, applique le ciblage d'entité et borne ensuite la sortie par Top-K (`ai/OpexAI/candidates.nut:1241-1305`). Le problème de tranchage C77 est dans le scheduler, lot 29.

### Lot 13 — Candidats route

**Aucun finding matériel dans le générateur.** `OpexRoadFreightCandidates` et `OpexBuildRoadCandidates` appliquent bien filtres d'entité et de cargo (`ai/OpexAI/candidates.nut:1673-1852`, `:1859+`). Le défaut C77 vient de la valeur de cargo transmise, lot 33.

### Lot 14 — Candidats rail

**Aucun finding matériel.** Les chemins pax/fret appliquent correctement les filtres town/industry (`ai/OpexAI/candidates.nut:1042-1236`).

### Lot 15 — Candidats AIR

**Aucun finding matériel.** Le ciblage de ville passe jusqu'à `OpexAirPlans` et aucun retour des politiques AIR abandonnées n'a été trouvé.

### Lot 16 — Candidats eau

**Aucun finding matériel.** Le chemin actif borne sites, fronts, BFS et pool projets (`ai/OpexAI/builder_water.nut:1-10`, `:133+`, `OpexWaterPlans` à `:330`). Cela ne change pas la décision C67 de remplacement futur.

### Lot 17 — Portefeuille projets

**Aucun finding matériel hors coordination C77.** Les clés, groupes d'alternatives et réinsertions conservent les modes ; `OpexProjectRememberAll` garde toutes les alternatives (`ai/OpexAI/projects.nut:495-511`).

### Lot 18 — Arbitrage et priorités

**Aucun finding matériel.** La sélection finançable recalcule `fundScore` selon C69/C70 actifs (`ai/OpexAI/projects.nut:625-719`) et le bonus early-slot reste cantonné au score final (`:722-752`).

### Lot 19 — Budget et financement

**Aucun finding matériel.** Les mesures et la réserve ont été relues ; aucun nesting actif démontré ne corrompt le budget.

### Lot 20 — Builder route

**F-ROAD-TXN-01 — rollback non atomique après démarrage partiel.**

- **Fichier:ligne :** `ai/OpexAI/builder_road.nut:748-756`, `:1134-1163`.
- **Trigger :** ligne à plusieurs véhicules ; un véhicule est déjà démarré, puis un `StartStopVehicle` suivant échoue.
- **Impact :** `OpexRoadRollback` tente de vendre les véhicules sans vérifier le résultat puis retire dépôt, arrêts et routes ; un véhicule déjà parti peut survivre sans ligne propriétaire.
- **Preuve :** démarrage séquentiel à `:1157-1163` ; rollback inconditionnel à `:748-756`. Le modèle peut demander deux véhicules (`ai/OpexAI/economy.nut:628-643`).
- **Incertitude :** aucun refus de démarrage n'a été reproduit runtime.

### Lot 21 — Builder rail

**F-RAIL-START-01 — démarrage de train non vérifié.**

- **Fichier:ligne :** `ai/OpexAI/builder_rail.nut:1242-1249`, `:1742-1763`.
- **Trigger :** `AIVehicle.StartStopVehicle(train)` retourne false.
- **Impact :** le builder peut retourner succès et persister un train resté au dépôt.
- **Preuve :** retour de `StartStopVehicle` ignoré puis `result.ok=true`.
- **Incertitude :** fréquence du refus non mesurée.

**F-RAIL-DEPOT-01 — démolition réelle avant probe de dépôt.**

- **Fichier:ligne :** `ai/OpexAI/builder_rail.nut:1065-1092`.
- **Trigger :** tuile candidate démolissable, puis `BuildRailDepot` échoue en `AITestMode`.
- **Impact :** terrain/infrastructure déjà modifié et payé sans dépôt ni restauration associée.
- **Preuve :** `AITile.DemolishTile(candidate)` à `:1076` précède la portée test `:1082-1085`.
- **Incertitude :** exposition terrain/NewGRF non mesurée.

**F-RAIL-TXN-02 — fuite de consist sur échec du second train.**

- **Fichier:ligne :** `ai/OpexAI/builder_rail.nut:1136-1238`, `:1995-2017` ; appel actif `ai/OpexAI/task_rail.nut:329-365`.
- **Trigger :** `RAIL_REFLEET` actif, ligne double avec `depot2`, échec wagon/MoveWagon/ordre du second train.
- **Impact :** locomotive/wagons partiellement construits peuvent rester hors `line.vehicles`, consommant capital et slots.
- **Preuve :** `OpexBuildTrains` accumule `rollbackVehicles`; `OpexBuildSecondTrain` jette ce tableau et retourne seulement `TRAINFAIL`.
- **Incertitude :** fréquence API non mesurée ; `policy_rail=1` active `RAIL_REFLEET` par défaut.

### Lot 22 — Builder AIR

**F-AIR-ORDER-01 — partage d'ordres du fallback non vérifié.**

- **Fichier:ligne :** `ai/OpexAI/builder_air.nut:839-859`, `:2095-2117` ; croissance `ai/OpexAI/task_air.nut:740-749`.
- **Trigger :** `CloneVehicle` échoue, `BuildVehicleWithRefit` réussit, mais `AIOrder.ShareOrders` échoue.
- **Impact :** avion démarré et compté dans la flotte sans garantie d'avoir les ordres de la ligne.
- **Preuve :** les appels `ShareOrders` à `:845` et `:2102` ne testent pas leur retour.
- **Incertitude :** échec non reproduit runtime.

Le risque de rollback après démarrage partiel d'une flotte initiale multi-avions reste une dette secondaire ; le chemin initial courant est borné à un avion sous portefeuille flotte (`builder_air.nut:694-704`).

### Lot 23 — Builder eau

**Aucun finding matériel.** Quais, connectivité, dépôt, refit, ordres et démarrage ont des contrôles/rollback ; le refleet navire vérifie aussi ordres et démarrage (`ai/OpexAI/builder_water.nut:487-688`).

### Lot 24 — Création et cycle de vie des lignes

**F-LIFE-SCRAP-01 — vente supposée réussie pendant le scrap.**

- **Fichier:ligne :** `ai/OpexAI/task_report.nut:465-531`, comparatif `:555-580`.
- **Trigger :** véhicule `IsStoppedInDepot` mais `SellVehicle` retourne false.
- **Impact :** le véhicule n'est pas remis dans `remaining`; la ligne peut être retirée comme `all_sold` alors que l'actif existe encore.
- **Preuve :** `SellVehicle(v)` à `:483` n'est pas testé ; le chemin de retraite unitaire teste correctement le booléen à `:563-575`.
- **Incertitude :** fréquence d'un refus de vente au dépôt non mesurée.

La sortie timeout après deux ans (`task_report.nut:495-524`) est volontaire et documentée ; elle n'est pas requalifiée en bug dans cette revue.

### Lot 25 — Gestion de flotte

**Finding transversal : F-AIR-ORDER-01.** Le rail hérite aussi de F-RAIL-START-01/F-RAIL-TXN-02. Aucun nouveau défaut distinct eau/route n'a été démontré.

### Lot 26 — Ordres véhicules

**F-RAIL-ERR-01 — ORDFAIL conserve un code d'erreur nul/ancien.**

- **Fichier:ligne :** `ai/OpexAI/builder_rail.nut:1142`, `:1234-1238`.
- **Trigger :** `AppendOrder` échoue après construction réussie de la locomotive.
- **Impact :** le rollback est déclenché correctement, mais diagnostic/ledgers reçoivent `lastError` qui n'a été mis à jour que sur un échec de `BuildVehicle`.
- **Preuve :** aucun `AIError.GetLastError()` n'est capturé après `AppendOrder`.
- **Incertitude :** impact comportemental direct nul démontré ; finding d'instrumentation.

### Lot 27 — Scheduler principal

**Aucun finding matériel.** Le scheduler historique conserve dueCycle/cursor et le worker rail enchaîne la file de fond.

### Lot 28 — Tâches reprenables

**F-C80-TOWN-01 — town-growth résumable retombe sur le scan monolithique si un autre worker occupe le registre.**

- **Fichier:ligne :** `ai/OpexAI/scheduler_tasks.nut:593-651`, `ai/OpexAI/task_town.nut:221-230`, `ai/OpexAI/orchestrator.nut:537-559`.
- **Trigger :** `C80_WORKER_TOWN=1`, tâche town-growth due pendant un worker d'un autre type, typiquement `rail_search`.
- **Impact :** le passage rescane toutes les villes servies jusqu'à un succès sans curseur ni budget de tranche, annulant temporairement le bénéfice du worker résumable.
- **Preuve :** commentaire explicite `scheduler_tasks.nut:638-640`, puis appel à `_tryTownGrowth` monolithique `:643-651`.
- **Incertitude :** `c80_worker_town` vaut 0 par défaut ; coût dépend du nombre de villes.

### Lot 29 — Bornage des scans

**F-C77-SLICE-01 — `regen_candidates` ne consomme pas son budget/deadline.**

- **Fichier:ligne :** `ai/OpexAI/orchestrator.nut:303-338`, `:523-572`.
- **Trigger :** C77 activé, worker `regen_candidates` actif.
- **Impact :** refresh catalogue + régénération complète d'un mode s'exécutent synchroniquement ; la branche générique retourne avant la file de fond, donc maintenance/scheduler peuvent être retardés.
- **Preuve :** `opsBudget` et `deadlineTick` sont reçus à `:307` mais jamais utilisés ; appels lourds `:318-327` ; retour anticipé `:560-567`.
- **Incertitude :** C77 vaut 0 par défaut ; coût carte-dépendant.

### Lot 30 — Événements

**F-EVENT-BACKLOG-01 — file d'événements vidée sans quota.**

- **Fichier:ligne :** `ai/OpexAI/events.nut:281-358`, appel `ai/OpexAI/main.nut:554-560`.
- **Trigger :** backlog/rafale d'événements.
- **Impact :** le scheduler et la file de fond ne reprennent qu'après vidage complet ; certains handlers déclenchent en plus invalidations/refresh.
- **Preuve :** boucle `while (AIEventController.IsEventWaiting())` sans compteur, deadline ni yield.
- **Incertitude :** saturation non démontrée en banc ; flux usuel probablement faible.

### Lot 31 — Handlers événements

**Aucun finding matériel distinct.** `IndustryOpen` route bien `[rail, road]` avec l'ID industrie (`ai/OpexAI/event_handlers.nut:539-547`).

### Lot 32 — C76 régénération ciblée

**Aucun finding matériel.** Révisions, coalescence et filet périodique correspondent au contrat courant ; le reload force la reconstruction C76 nécessaire.

### Lot 33 — C77 candidats opportunistes

**F-C77-CARGO-01 — cargo fret trouvé par le rail ciblé non propagé à la route ciblée.**

- **Fichier:ligne :** `ai/OpexAI/event_handlers.nut:542-547` ; `ai/OpexAI/events.nut:124-138` ; `ai/OpexAI/projects.nut:1004-1052`, `:1118-1131` ; `ai/OpexAI/candidates.nut:1700-1702`.
- **Trigger :** `IndustryOpen` dont le cargo pertinent diffère de `projects.freightCargo`.
- **Impact :** le rail peut fallback vers un autre cargo et injecter un projet, puis la route relit l'ancien cargo et filtre strictement les autres ; les candidats route immédiats de l'industrie peuvent être totalement manqués jusqu'à rotation/régénération complète.
- **Preuve :** `generated.freightCargo` est mis à jour par le fallback rail, mais n'est recopié dans `projects.freightCargo` que sous `!targeted`.
- **Incertitude :** fréquence climat/NewGRF/cargo courant ; logique déterministe si le trigger est exposé.

**Finding transversal : F-C77-SLICE-01.**

La limite déjà documentée « C77 sans C76 perd les candidats injectés lors d'une régénération complète » reste une limite connue, pas un nouveau finding de cette revue.

### Lot 34 — Persistance : sérialisation

**Aucun finding matériel.** `Save()` projette les lignes en un passage et persiste C69/C75, scheduler, retraites, subventions, rail expansion, C80/C76 (`ai/OpexAI/persist.nut:386-488`).

### Lot 35 — Persistance : restauration

**Aucun finding matériel.** `Load()` reste field-guarded et diffère la lecture monde à `Start()/reconcile` (`ai/OpexAI/persist.nut:490-551`).

### Lot 36 — Réconciliation après Load

**Aucun finding matériel.** L'ancien problème C69/C70/C75 est corrigé : dates restaurées après settings, lignes vivantes reconstruites, puis C70/C82 recalculés (`ai/OpexAI/persist.nut:554-622`).

### Lot 37 — Save/Load sous charge

**Aucun finding matériel nouveau.** Le Save courant utilise la projection unique qui remplace le double scan ; aucun crash Save n'a été reproduit ou retrouvé au HEAD.

### Lot 38 — Gestion des erreurs

**F-AIR-ERR-01 — `AIError` potentiellement périmé sur HUB/HUBB.**

- **Fichier:ligne :** `ai/OpexAI/builder_air.nut:1997-2019`, `:2022-2048` ; consommation `ai/OpexAI/task_air.nut:377-418` ; garde d'abandon `ai/OpexAI/lines.nut:31-42`.
- **Trigger :** réutilisation demandée d'un aéroport disparu/incompatible ; la branche échoue sans commande API fautive immédiate.
- **Impact :** logs/ledgers peuvent attribuer une mauvaise erreur ; un faux `ERR_NOT_ENOUGH_CASH` rend l'échec transitoire et peut empêcher la mémoire d'abandon.
- **Preuve :** `result.error = AIError.GetLastError()` est lu dans ces branches sans appel échoué nécessaire juste avant.
- **Incertitude :** valeur concrète du last-error non observée runtime.

**Finding transversal : F-RAIL-ERR-01** pour les ordres rail.

### Lot 39 — Nettoyage après échec construction

**Findings matériels : F-ROAD-TXN-01 et F-RAIL-TXN-02.**
Le chemin AIR conserve volontairement `airportA` après `BFAIL` lorsque la maintenance d'infrastructure vaut 0 (`ai/OpexAI/builder_air.nut:2038-2048`) et rescane ces aéroports comme hubs (`:1559-1577`) : dette/coût possible, mais pas corruption prouvée et donc pas requalifié ici comme finding principal.

### Lot 40 — Crashs / véhicules disparus

**Aucun finding matériel nouveau.** Les handlers crash/refleet et remaps d'autoreplace sont présents. Le timeout de scrap qui peut abandonner un véhicule vivant hors `_lines` est explicitement assumé dans `task_report.nut:495-524` pour éviter un blocage permanent ; il n'est pas rouvert comme bug. C52 reste clos/default 0.

### Lot 41 — Note municipale

**Aucun finding matériel.** Le filtre C60 reste désarmé et les probes ne montrent pas de refus réel justifiant de le rouvrir.

### Lot 42 — Territoire / occupation physique

**Aucun finding matériel.** Les claims early-slot sont recalculés depuis l'état physique avant sélection et restent distincts du profit économique.

### Lot 43 — Probes

**Aucun finding matériel comportemental.** Les probes sont gardées et à 0 par défaut ; le helper de signs a un défaut propre au lot 45.

### Lot 44 — Ledgers

**Aucun finding matériel.** Les ledgers inspectés sont gardés/resetés selon leurs probes ; aucun compteur de diagnostic n'a été trouvé dans une décision hors contrat.

### Lot 45 — Logs / signs

**F-SIGN-01 — `OpexSign` ne respecte pas systématiquement la limite de 31 caractères.**

- **Fichier:ligne :** `ai/OpexAI/probes.nut:36-40` ; `ai/OpexAI/info.nut:18-24` ; `ai/OpexAI/task_report.nut:682-724` ; commentaire `ai/OpexAI/main.nut:24-25`.
- **Trigger :** `debug_signs=1` (défaut) et texte composé dont les compteurs deviennent longs.
- **Impact :** panneau absent/illisible et métrique sweep perdue ; cadence éventuellement modifiée par l'erreur API.
- **Preuve :** `OpexSign` transmet directement `name` ; `bcText` est tronqué à 31, contrairement à plusieurs autres textes.
- **Incertitude :** aucun compteur concret du banc courant n'a été mesuré pour prouver un dépassement sur une graine donnée.

### Lot 46 — Coût opcode

**Findings matériels : F-C80-TOWN-01, F-C77-SLICE-01 et F-EVENT-BACKLOG-01.** Hors ces chemins, aucun nouveau scan infini/non borné matériel n'a été démontré.

### Lot 47 — `bench_v2.py`

**Aucun finding matériel.** Horizon incomplet, checkpoints non contigus et décodage physique invalide provoquent un échec de protocole explicite (`sweeps/bench_v2.py:661-713`).

### Lot 48 — `physical_counters.py`

**Aucun finding matériel.** Le décodeur sépare têtes/composants, filtre le propriétaire et fail-closed sur les anomalies (`sweeps/physical_counters.py:143-230` et suites).

### Lot 49 — `game_health.py`

**Aucun finding matériel.** Erreur moteur, données manquantes, doublons, NoAI error, horizon tronqué, faillite et inactivité sont distingués (`sweeps/game_health.py:482-571`).

### Lot 50 — `campaign_freeze.py`

**Aucun finding matériel.** Réglages inconnus/différences non annoncées sont refusés (`sweeps/campaign_freeze.py:183-213`) et les bibliothèques/configs sont figées avec empreintes.

### Lot 51 — Duel C66 / causal harness

**Aucun finding matériel.** Le harnais conserve les contrôles d'identité/santé et les règles d'adoption ; les runs absents/échoués ne sont pas transformés en victoires.

### Lot 52 — Tests existants

**F-TEST-01 — dette de tests préexistante, sans finding runtime associé.**

- **Fichier:ligne :** `sweeps/test_b8_scrap_lifecycle.py:63-68`, `sweeps/test_review_evidence.py:18-38`, état courant `docs/taches.md:72-79`.
- **Trigger :** suite complète de contrats.
- **Impact :** la suite globale n'est pas un signal vert unique : le test feeder cherche encore `FEEDER_RECOVER` supprimé ; l'index de preuves est l'autre échec préexistant documenté.
- **Preuve :** recherche littérale de `FEEDER_RECOVER` dans le test ; `docs/taches.md` indique explicitement les deux échecs préexistants.
- **Incertitude :** la suite complète n'a pas été relancée par le prime ; les contrôles ciblés harnais exécutés pendant la revue sont verts.

### Lot 53 — Imports / bibliothèques tierces

**F-DOC-DEPS-01 — dérive documentation/provenance du chemin eau.**

- **Fichier:ligne :** runtime `ai/OpexAI/main.nut:28-30`, `ai/OpexAI/builder_water.nut:126-130` ; doc `docs/architecture_opexai.md:29-34`, `:159-170`.
- **Trigger :** audit, maintenance ou gel des dépendances depuis la documentation.
- **Impact :** un mainteneur peut croire que le runtime charge encore `lib_water.nut`/MinchinWeb Lakes et réintroduire ou figer une dépendance retirée.
- **Preuve :** le seul import runtime direct au début de `main.nut` est `pathfinder.rail`; `ai/OpexAI/lib_water.nut` n'existe plus au HEAD alors que le document d'architecture le décrit encore.
- **Incertitude :** Queue peut rester transitive via une bibliothèque tierce ; ne pas la retirer d'un freeze sans vérifier cette transitivité.

### Lot 54 — Code mort / compatibilité historique

**Aucun finding matériel à corriger automatiquement.** Les `*_OPCODE_COMPAT_FALSE`, slots scheduler historiques et fallbacks anciennes sauvegardes sont intentionnels ; les nettoyer sans protocole d'identité contredirait les décisions récentes.

## 4. Lot 55 — scénarios bout en bout

### Route

Flux : candidats route → `OpexRoadLineEconomics` → projet/financement → builder route → `_lines` → report/scrap → Save/Load.
Ruptures principales : F-ROAD-TXN-01 et F-LIFE-SCRAP-01. Elles partagent la même cause : le code perd la propriété d'un actif lorsque l'API refuse une opération après qu'un premier effet irréversible a déjà eu lieu. Sous C77, F-C77-CARGO-01 peut en plus supprimer l'opportunité avant le builder.

### Rail

Flux : candidats rail → `OpexLineEconomics` → portefeuille → A* reprenable → `OpexBuildTrains` → ligne → expansion/refleet → report/lifecycle → Save/Load.
Le rail concentre F-RAIL-ECON-01, F-RAIL-DEPOT-01, F-RAIL-START-01, F-RAIL-TXN-02 et F-RAIL-ERR-01. La persistance n'est pas la cause : le reload courant filtre/reconstruit correctement les lignes connues.

### AIR

Flux : `OpexAirPlans` / économie AIR → projet C69/C70 → `OpexBuildAirRoute` → ligne / `OpexAirAddPlane` → report C70/C82 → Save/Load.
Ruptures : F-AIR-ORDER-01 et F-AIR-ERR-01. Elles viennent de contrats API non vérifiés, pas du modèle C68 ni des politiques AIR abandonnées.

### Eau

Flux : recherche bornée de sites/fronts → `OpexWaterEconomics` → projet → builder eau → ligne/navire → refleet → Save/Load.
**Aucun finding runtime matériel nouveau.** Le principal écart est F-DOC-DEPS-01 : la doc ne correspond plus au chemin actif. C67 reste un chantier futur séparé.

## 5. Lot 56 — synthèse architecturale et causes racines

### RC1 — Transactions builders non atomiques après le premier effet irréversible

F-ROAD-TXN-01, F-RAIL-DEPOT-01, F-RAIL-TXN-02. Le motif commun est l'absence d'un contrat uniforme « probe/préparation → commit → rollback uniquement d'objets encore rollbackables ».

### RC2 — Retours booléens d'API traités comme infaillibles

F-RAIL-START-01, F-AIR-ORDER-01, F-LIFE-SCRAP-01. D'autres fonctions du dépôt vérifient correctement ces mêmes retours, ce qui confirme que l'omission est locale et non un contrat API assumé.

### RC3 — État implicite partagé entre étapes de régénération

F-C77-CARGO-01. `freightCargo` sert à la fois d'état global de rotation et de résultat local du rail ciblé ; le worker traite ensuite la route sans transporter explicitement le résultat.

### RC4 — Contrats de tranchage incomplets

F-C80-TOWN-01, F-C77-SLICE-01 et F-EVENT-BACKLOG-01. Le code possède une architecture de workers/budgets, mais certains chemins retombent sur des boucles monolithiques ou drainent un backlog avant de rendre la main.

### RC5 — Dérive modèle / coût réellement payé

F-RAIL-ECON-01. Le catalogue connaît déjà le coût du dépôt, mais l'économie ne l'utilise pas.

### RC6 — Instrumentation et documentation moins robustes que le métier

F-AIR-ERR-01, F-RAIL-ERR-01, F-SIGN-01, F-TEST-01, F-DOC-DEPS-01. Ces défauts réduisent la confiance dans les diagnostics et augmentent le risque de rouvrir des chemins supprimés.

## 6. Classement par catégorie demandée

| Catégorie | Conclusion |
|---|---|
| Crash / corruption | Aucun crash Save/corruption sauvegarde démontré ; risques d'actifs orphelins via F-ROAD-TXN-01, F-RAIL-TXN-02, F-LIFE-SCRAP-01. |
| Décision | F-RAIL-ECON-01 ; F-C77-CARGO-01 ; F-AIR-ERR-01 peut influencer l'abandon. |
| Persistance | Aucun finding matériel ; anciens défauts C69/C70/C75 revalidés corrigés. |
| Économie | F-RAIL-ECON-01 seulement ; aucune réouverture des politiques AIR abandonnées. |
| Coût opcode | F-C80-TOWN-01, F-C77-SLICE-01, F-EVENT-BACKLOG-01. |
| Builders | F-ROAD-TXN-01, F-RAIL-START-01, F-RAIL-DEPOT-01, F-RAIL-TXN-02, F-AIR-ORDER-01. |
| Instrumentation | F-AIR-ERR-01, F-RAIL-ERR-01, F-SIGN-01. |
| Harnais | Bench/health/physical/freeze propres ; F-TEST-01 est une dette de suite globale. |
| Dette architecturale | timeouts/intentionnels conservés ; F-DOC-DEPS-01 ; tranchage C77/C80 incomplet. |
| Compatibilité historique | gardes opcode false, slots historiques et fallbacks anciennes saves sont intentionnels. |

## 7. Lot 57 — ordre de correction proposé

1. **Atomicité et propriété des actifs sur chemins défaut** : F-ROAD-TXN-01, F-RAIL-TXN-02, F-LIFE-SCRAP-01, puis F-RAIL-START-01.
2. **Effets de bord rail avant validation** : F-RAIL-DEPOT-01.
3. **Contrats API AIR actifs** : F-AIR-ORDER-01 puis F-AIR-ERR-01.
4. **Modèle économique rail** : F-RAIL-ECON-01, avec validation de sélection/finançabilité après raccord de `costRailDepot`.
5. **Tranchage actif/optionnel** : F-EVENT-BACKLOG-01 d'abord car chemin défaut, puis F-C80-TOWN-01 et F-C77-SLICE-01.
6. **Avant tout nouveau banc d'adoption C77** : corriger ensemble F-C77-CARGO-01 et F-C77-SLICE-01.
7. **Fiabilité du diagnostic** : F-SIGN-01 et F-RAIL-ERR-01.
8. **Dette tests/docs** : F-TEST-01 et F-DOC-DEPS-01.
9. **Compatibilité intentionnelle en dernier** : ne pas simplifier gardes opcode, slots historiques, timeout scrap ou ancien format Save sans protocole d'identité/cadence explicite.

## 8. Limites de la revue

- Revue principalement statique : les chemins sont démontrés, mais la fréquence runtime de plusieurs refus API rares n'est pas mesurée.
- Aucun smoke économique ni Docker n'a été lancé spécifiquement pour cette revue.
- Un sous-audit a exécuté sans modification de sources : 8 tests `physical_counters`, 26 `game_health`, 11 `campaign_freeze` et le selftest C66, tous verts.
- La suite complète n'est pas déclarée verte : `docs/taches.md:78-79` conserve deux échecs préexistants, repris au lot 52.
- Les performances antérieures au 2026-09-09 ne sont pas utilisées comme preuve actuelle.
- Les findings C77/C80-worker sont conditionnels aux réglages désarmés par défaut ; ils sont des blockers d'évolution, pas des régressions du défaut livré.

## 9. Conclusion

Le HEAD courant ne montre ni corruption Save/Load ni retour des politiques abandonnées. Le risque principal est l'atomicité incomplète des builders/lifecycles et l'absence de vérification systématique de retours API : ces chemins peuvent produire des actifs physiques que `_lines` ne possède plus ou considérer une ligne comme réussie sans service.

Le second axe est la cohérence décisionnelle et de scheduling : le rail sous-estime son capital d'un dépôt ; C77 couple implicitement le cargo entre modes et exécute une régénération monolithique ; certains chemins C80/events contournent encore les principes de tranchage. Ces causes racines doivent être traitées avant de rouvrir une phase d'adoption ou d'optimisation économique.
