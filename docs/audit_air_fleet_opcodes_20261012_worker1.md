# Audit ciblé `air_fleet` 1970–1973 — lecture seule (12/10/2026)

**Statut : diagnostic, aucune modification de politique, aucun banc nouveau.**
Arbre lu : `/openttd-ml`, `master` `f6139d8`. Les travaux locaux déjà présents
restent intacts. Source chiffrée : `evidence/review/opcode_early4_20261012/`
(`breakdown.json`, `profiled_engine_logs.zip`, manifeste `profiled_5y.manifest.json`).
Les cinq graines sont 42, 100, 999, 1234, 5678. Les opcodes mesurent le
budget de la VM NoAI, **ticks franchis compris** : des suspensions de commandes
peuvent être facturées par tranches de 10 000 sans autant d'instructions CPU.

## Verdict sur la nature des 10,9 M de 1973

L'intitulé `air_fleet_no_work` **ne prouve pas que ce travail est inutile**.
`ledgers.nut:718-725` teste une égalité d'identité d'objet
`this._projects == this._schedIdlePreProjects` et une égalité du nombre total
de véhicules, puis publie `w=0`. Or `_dispatchAirFleet`
(`scheduler_tasks.nut:941-963`) demande les opportunités en mode à blanc,
les convertit si `fleetPlan.len() > 0`, puis injecte dans le portefeuille.
`OpexInjectFleetProjects` (`projects_update.nut:5-42`) **réécrit les champs de
`projects` en place** (`candidateGroups`, statistiques, `best`) et
`OpexReselectProjects` (`projects_selection.nut:1940-2045`) retourne finalement
**le même objet `projects`**. Une sélection réelle peut donc être systématiquement
classée `no_work`. Les décisions de construire sont arbitrées plus tard par la
tâche `projects` : l'absence d'achat *dans* `air_fleet` est normale avec
`FLEET_PORTFOLIO=1`.

Pour départager les dépenses, on a relu les cinq journaux moteur archivés.
Méthode : pour chaque `SCHED_IDLE t=air_fleet`, isoler les lignes apparues
**depuis le dernier `SCHED_IDLE` précédent**, additionner exclusivement les
`SELECTION_LIGHT path=reselect ops=...` de cette fenêtre et comparer au
`op=...` de la tâche. La réélection ne se produit dans ce dispatcher que si
`fleetPlan.len() > 0`. Ainsi une occurrence de `reselect` constitue une preuve
de **plan de flotte non vide**, pas une preuve de modification effective du
portefeuille final ni d'achat. Les mesures `SELECTION_LIGHT` sont incluses
dans `SCHED_IDLE`, jamais additionnées à la comptabilité globale `LOOP_OPS`.

| Année | Passages `air_fleet`/graine | Coût tâche M/graine | Dont `reselect` M/graine | Part `reselect` | Passages avec `reselect`/graine |
|---|---:|---:|---:|---:|---:|
| 1970 | 139,6 | 1,594 | 1,057 | 66,3 % | 31,8 |
| 1971 | 186,2 | 2,675 | 1,378 | 51,5 % | 42,8 |
| 1972 | 80,0 | 9,992 | 6,186 | 61,9 % | 10,4 |
| **1973** | **45,0** | **10,886** | **5,965** | **54,8 %** | **28,8** |

Ce tableau est recalculé sur les lignes `SCHED_IDLE` (les dates réelles des
journaux), d'où un petit écart avec les **10,940 M** de `C39 task|air_fleet`
en 1973 : C39 retraite les frontières du rapport annuel. Les 10,886 M
correspondent exactement à l'agrégat `idle` de `breakdown.json`. Les 5,965 M
sont **une mesure du sous-poste** de sélection, pas une estimation à partir
du nombre de lignes aériennes.

| Graine, année 1973 | Passages | Avec `reselect` | Coût total M | Coût `reselect` M |
|---|---:|---:|---:|---:|
| 42 | 47 | 46 | 14,468 | 4,967 |
| 100 | 135 | 65 | 11,399 | 3,739 |
| 999 | 7 | 7 | 9,561 | 7,878 |
| 1234 | 20 | 10 | 7,923 | 6,532 |
| 5678 | 16 | 16 | 11,081 | 6,707 |

La très grande différence de fréquence (**7 à 135** passages) déconseille
d'extrapoler un coût moyen par passage à d'autres populations. Le reliquat
**4,922 M en 1973** (10,886 - 5,965 M) recouvre toute la génération du plan,
la copie/épuration/injection des candidats, la partie non couverte par
`SELECTION_LIGHT`, et les charges de diagnostic : il **ne démontre pas** que
4,922 M vont au simple contrôle des refus de croissance.

## Chemin d'exécution et gardes effectives

- `scheduler.nut:293-350` sélectionne la tâche ;
  `scheduler_tasks.nut:947-961` met `dueCycle = _taskCycle + 1`, reconstruit le
  plan et appelle `OpexInjectFleetProjects` uniquement si plan non vide.
  Même sans construction physique, cela peut déclencher une sélection
  globale de tous les modes.
- `_resizeAirFleets` (`task_air.nut:1069-1373`) filtre les lignes en cadence
  **avant le tri**, trie une copie puis vérifie, dans cet ordre, liquidation,
  rééquipement V92, crash/refleet, cadence, existence d'avion, cible,
  maturité C121, santé/profit, plafond physique, prix/capacité et besoin.
  En mode `plan != null`, les gardes de financement et l'achat (`:1342-1369`)
  **ne sont pas exécutés**, c'est le portefeuille qui décide.
- Le manifeste confirme `policy_air=1`, `policy_caches=1`,
  `c121_air_economics=1`, `c121_air_first_live_growth=1` (phase quatre ans),
  `air_fleet_cadence_days=7`, `air_fleet_cooldown_prefilter=1`,
  `exp_opcode_exact=1`, `c121_air_visible_competition=0`,
  `c84_air_target_fleet=0`, `v92_air_service_choice=0` et
  `c69_decision_bottleneck=1` ; `AIR_FLEET_BUFFER=0` **après chargement**
  (`settings.nut:661` écrase le repli initial `globals_pre.nut:771` à -1).
  Ainsi `OpexC121RefreshVisibleFleet` (`air_fleet.nut:316-320`) **retourne
  immédiatement** au défaut. Le chemin tampon de stock
  (`task_air.nut:1277-1305`) reste **exécutable quand `c121BelowTarget`
  est faux**, puisque le tampon effectif est zéro. Les renforts
  sous cible C121 passent directement par `:1271-1276`, sans exiger
  un avion entier en stock ; leurs premières admissions dépendent des
  données live/annuelles selon `:1181-1222`.
- Les optimisations **déjà actives et qualifiées** sont le préfiltre par ligne
  (`task_air.nut:1077-1109`) et le tri avec rendement précalculé
  (`:1110-1113`, `opcode_exact.nut:724-779`). Elles ne sont pas des pistes
  à redévelopper. Voir `docs/journaux/journal_2026-10-02.md:472-493` et
  `docs/opcode_exact_20261002.md`.
- Le `dirty/next-due` global a été **définitivement rejeté** :
  410 scans de référence, 412 scans variante, **zéro skip** et opcodes plus
  élevés. Voir `docs/journaux/journal_2026-10-02.md:429-439`.

## Une seule optimisation locale candidate, distincte des rejets

**Mutualiser, au sein d'un passage de contrôle de flotte, le nombre de lignes
AIR vivantes par station** demandé par `OpexAirCadenceCap`.
`air_trip.nut:124-163` appelle deux fois
`OpexAirLiveRoutesAtAirport` (`:82-103`) par ligne éligible ; chacun de ces
appels reparcourt **toutes** les lignes et cherche au moins un avion valide,
puis résout les deux tuiles de station. Pour L lignes, la partie pertinente
est potentiellement O(L²). Un index local `stationId -> nombre de lignes AIR
vivantes`, rempli en un seul parcours et consulté dans la même passe, est
potentiellement O(L). Compter **une seule fois** une ligne reliant deux
extrémités de la même station, respecter l'absence de véhicule valide, les
stations invalides et les formes `vehicle`/`vehicles` existantes.

**Condition de sûreté :** aucun cache durable. Conserver un chemin historique
fallback lorsque le tick change (`AIController.GetTick()`), qu'un véhicule est
recréé/retiré au cours de la passe (notamment `needsRefleet`), ou que V92 est
activé. Le contrôle en shadow doit comparer, **sur les mêmes entrées**, les
deux décomptes par `stationId`, les deux plafonds entiers de cadence et la
liste ordonnée des opportunités `lineId,want,planePrice` avant d'autoriser
le résultat neuf. Aucun changement du score ni du cooldown n'est permis.
Un cache per-tick peut être trop souvent invalidé et ne rien gagner : mesurer
le coût réel net **avant** tout essai A/B de qualification. Le fait que
`reselect` représente 54,8 % du poste **ne prouve pas** que ce cache soit
rentable : le levier vise seulement le coût du scanner de cadence.

## Instrumentation passive minimale nécessaire

Sous un flag OFF par défaut, faire un **registre annuel agrégé, pas des logs
par ligne** : passes de `air_fleet`, `fleetPlan.len()`, nombre de lignes avant
et après préfiltre, motif de premier refus (Y/V/O/D/L/C/S/W/K/R/T), appels
et coût `OpexAirCadenceCap`/`OpexAirLiveRoutesAtAirport`; coûts séparés
`resize`, `inject.filter_and_copy`, `inject.convert_fleet`,
`reselect.flatten_and_filter`, `reselect.fit_and_score`, et `reselect.stats`.
Ne pas additionner les postes imbriqués au total : instrumenter de vrais
segments exclusifs, contrôler les franchissements de tick et faire coïncider
les sommes avec `SCHED_IDLE`. Pour le statut de travail, relever après
injection le nombre de projets fleet **avant/après**, le nombre de candidats
admissibles et les identités du `best`, car l'identité de `_projects` est
insuffisante.

Gates de vérification : d'abord tests de contrat (parité exact de la fonction
comptable sur formes edge/invalides, priorité crash et V92, aucun état à
sauvegarder), puis smoke moteur apparié, sonde old/new et coût médian/total
sur les mêmes seeds ; si économie opcode effectivement démontrée, appliquer
le protocole d'optimisation opcode du dépôt : 20×10 apparié sain, IC95 de
`profit_year` pas entièrement négatif, test des signes sans défaite
significative, garde de valeur -5 %. Ne **jamais** remobiliser le rejet
`air_fleet_dirty_sched` ou inférer un gain opcodes du seul statut `w0`.

## Limites

Les cinq parties profilées emploient `probe_scheduler=1` et
`catalog_cost_probe=1`, ce qui peut modifier les trajectoires. Les ratios
sont descriptifs, non causalement transposables au témoin non sondé.
Les opcodes de sélection peuvent recouvrir des ticks d'attente et les appels
de `_resizeAirFleets` dans la **tâche `catalog`** (`scheduler_tasks.nut:390-395`)
ne figurent pas dans le coût de la tâche `air_fleet` : la contribution réelle
de l'analyse de flotte au budget de la partie peut donc être supérieure à
cette catégorie seule. Aucun essai Docker, correctif Squirrel, commit ou
push n'a été réalisé pour cet audit.
