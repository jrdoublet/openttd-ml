# Plan de revue de code — 2026-09-15

Demandée le 2026-09-15, découpée en étapes pour tenir dans le quota. Reprend la forme des deux
revues précédentes (2026-09-01/02, puis `revue_code_2026-09-06_plan.md` → 40 constats →
`revue_code_2026-09-06_correctifs.md`) : un lot cohérent par étape, un écrit de constats par
étape, rien de corrigé au passage.

## Pourquoi un découpage, et pourquoi celui-là

`ai/OpexAI/` pèse **28 868 lignes sur 34 fichiers** (1,46 Mo ≈ 365 k tokens). Une revue en une
passe est matériellement impossible : le seul chargement du code dépasse la fenêtre de contexte.
La revue du 09-06 portait sur 17 190 lignes ; le code a crû de **+68 %** depuis, et surtout
**C65 (2026-09-13) a découpé `main.nut` (≈ 4 900 l.) en 20 modules** qui n'ont jamais été relus
sous leur forme actuelle.

**Périmètre retenu** : `ai/OpexAI/` (28 868 l.) + le **harnais de banc actif** (`sweeps/`, 5 635 l.
sur les 45 134 du répertoire — seuls les scripts qui arbitrent encore des décisions) + la
**couture avec `ai/library`** (les points d'appel MinchinWeb/SuperLib, pas les bibliothèques
tierces elles-mêmes, 16 374 l. hors périmètre).

**Ordre retenu** : strictement des couches basses vers le haut — des feuilles dont rien ne dépend
vers l'orchestration qui dépend de tout. Pas d'étape d'audit préalable.

## Méthode

Reprise du 09-06, plus deux règles neuves :

- **Diagnostic seulement.** Aucun correctif dans cette passe, même évident — noter, ne pas coder.
- **Vérifier à la main, pas par grep seul.** Un réglage lu par du code mort paraît actif :
  `preplan_queue` était *lu* par `info.nut` mais son seul site d'appel vivait dans `_tryPreplan`,
  jamais invoqué.
- **Vérifier le défaut avant de crier au code mort.** 145 des 227 réglages sont à 0 **par
  conception** (drapeaux d'expérience banqués et rejetés, ou pas encore banqués) ; 82 seulement
  sont actifs. Voir `ai/OpexAI/CLAUDE.md`, section « Ce qui ressemble à un bug mais n'en est pas ».
- **Noter aussi ce qui N'EST PAS un bug**, pour ne pas le relitiger à la passe de correction.
- *(neuf)* **Un constat de mesure vaut un constat de logique.** Le mode d'échec dominant du projet
  est l'artefact de mesure, pas l'erreur de calcul : comptage `VEHS` non qualifié (C54) qui a fait
  retirer le diagnostic « 93 % de rendement par véhicule » ; `build_failed` 1 795 re-mesuré à 50
  (÷ 36) ; 4 faux positifs de santé du harnais rouverts le 09-14. Chaque étape regarde ce que son
  code *prétend* mesurer autant que ce qu'il calcule.
- *(neuf)* **Ancrer chaque constat sur `fichier:ligne` et le SHA revu.** Les numéros de ligne
  `main.nut` antérieurs à C65 sont périmés ; un constat sans ancrage sera invérifiable dans
  quinze jours.

## Discipline de quota

C'est la contrainte qui a dicté le découpage, pas un commentaire d'accompagnement.

- **1 étape = 1 session neuve.** Ne jamais enchaîner deux étapes dans la même session.
- **Plafond : ≈ 2 200 lignes de source lues par étape** (≈ 28 k tokens). Le tableau le respecte
  partout sauf l'étape 1, dont l'exception est documentée. Les étapes 3 (2 280 l.) et 17
  (2 238 l.) le dépassent de 80 et 38 lignes : découper l'une ou l'autre casserait un lot
  fonctionnel pour moins de 4 % de volume, le « ≈ » les couvre.
- **Contexte d'amorçage autorisé et suffisant** : `ai/OpexAI/CLAUDE.md` (153 l., écrit exactement
  pour ça) + la ligne du tableau de l'étape + les fichiers de l'étape. Rien d'autre.
- **Interdits explicites** — c'est ce qui fait exploser le quota : `docs/taches.md` en entier
  (860 l.), les `docs/journal_*.md` en entier, `results/*.json` (22 Mo), `sweeps/` hors des
  étapes 17-19, `ai/library/` (16 374 l. de code tiers).
- **Pour vérifier un réglage** : `grep -n "<nom>" info.nut settings.nut globals_*.nut` plutôt
  qu'ouvrir `info.nut` (2 746 l.).
- **Un fichier de constats par étape**, jamais un fichier partagé : une session qui doit relire
  les constats des quatorze étapes précédentes pour y ajouter les siens repaye tout le quota déjà
  dépensé.

## Tableau des étapes

Modèle et effort sur l'échelle du skill `/code-review` (low/medium/high/xhigh/max). Mapping Codex
repris du 09-06 : **sol ≈ Opus**, **terra ≈ Sonnet**.

### Couche 1 — configuration

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 1 | `info.nut` *(lecture déclarative)*, `settings.nut`, `globals_pre.nut`, `globals_post.nut` | 3 809 | **Opus 5** / high | **A. Cohérence de la couche.** 227 `AddSetting` contre 213 `GetSetting` contre les globales : réglages déclarés jamais lus, lus jamais déclarés, replis divergents. **8 globales définies en double voire en triple**, la valeur finale étant décidée par l'ordre de chargement : `CLEAN_DENSITY_SCORE` (`globals_pre:32` + `candidates:74` + `projects:38`), `TOP_K` (`globals_post:8` + `candidates:26`), `OPS_PER_TICK`, `AIR_FULL_LOAD`, `AIR_JOINED_STOPS`, `FEEDER_PRICING`, `FEEDER_TOWN_COVERAGE`, `FEEDER_UNLOCK`. **B. Audit d'adoption.** Pour chacun des 82 défauts actifs, retrouver le banc qui l'a fait basculer et vérifier qu'il s'agit du **banc officiel** (20 graines × 10 ans apparié, ≥ 15/20 au test des signes, p < 0,05). Quatre cas déjà identifiés comme douteux ouvrent la liste — voir l'encadré ci-dessous. |

**Exception de plafond assumée** : `info.nut` est lu en mode déclaratif (grep sur les
`AddSetting`, pas de lecture ligne à ligne) — la prose descriptive n'a pas à passer en contexte.

> **Encadré — la liste d'amorçage du volet B.** Quatre défauts actifs reposent sur un banc plus
> faible que le banc officiel, c'est-à-dire exactement la configuration qui a produit l'erreur
> C29.3 rattrapée par C31 :
>
> | Réglage | Adopté | Banc | Problème |
> |---|---|---|---|
> | `feeder_mail_strict_orders` | 09-15 | 5 graines × 3 ans, **0/5 victoire**, −332 789 £ de valeur, −244 569 £/an | Ni 20 graines, ni 10 ans, ni p-value, et **économiquement négatif**. Adopté comme correctif fonctionnel. |
> | `c53_order_nonstop` | 09-11 | 20 × 10 : +2,44 % valeur, 11 V / 8 D / 1 ég., **p = 0,648** | Non significatif ; recompté le 09-13 comme « adopté ≠ gain démontré ». |
> | `water_lakes_ops_budget` | 09-11 | 20 × 10 : score 8/0/12 p = 0,008 ; **valeur 7/1/12 p = 0,070** | Sous le critère sur la valeur ; adopté sur « suppression d'un mode d'échec dur ». |
> | `event_vehicle_autoreplaced` | 09-11 | **aucun banc**, décision utilisateur ; 33/33 événements `untracked` sur 16 ans | Le réglage serait par ailleurs ignoré par le code — à trancher à l'étape 12. |
>
> Ces quatre-là sont le point de départ, pas la conclusion : le volet B couvre les 82.

### Couche 2 — feuilles et primitives

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 2 | `budget.nut`, `capital.nut`, `spatial.nut`, `probes.nut`, `lines.nut` | 1 687 | Sonnet 5 / medium | Compteur d'opcodes (`GetOpsTillSuspend` rend le **reste du tick courant**, pas un stock — un bloc de travail qui traverse des ticks ne peut pas se mesurer par soustraction de deux restes), réserve de trésorerie et emprunt, grille spatiale C46, canal de mesure `OpexSign`/`OpexDecide`, identité/jointure/abandon de ligne. `OpexAbandonedPairKey` (`lines.nut:268`) a été retouchée depuis le constat G9 du 09-06 : **vérifier la fermeture, pas rouvrir le constat**. |

### Couche 3 — données de référence et scoring

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 3 | `catalog.nut`, `economy.nut`, `tension.nut` | 2 280 | Sonnet 5 / high | G12 ouvert (le catalogue réduit chaque cargo à son matériel le plus capacitaire **avant** tout calcul de ROI ; l'aérien ne garde qu'un avion par type d'aéroport, sur rang plutôt que sur ROI). G3 ouvert (le rail chiffre capacité, fréquence et temps de paiement sur la **distance candidate**, jamais sur le tracé A* trouvé — la route fait déjà cette remise à l'échelle, c'est le patron à répliquer). `tension.nut` reste inerte (`tension_scoring` et `shadow_pricing` à 0, C35.3/4/5 rejetés au banc) : effort réduit sur ce tiers, sauf les 154 lignes de code mort signalées en 2026-09-06 (`OpexTensionMacroRegime`). |

### Couche 4 — génération de candidats

`candidates.nut` (3 472 l.) est coupé sur une frontière de fonction, à l'entrée de
`OpexBuildCandidates`.

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 4 | `candidates.nut:1-1852` — cinématique et bornes d'époque, index de lignes, jointure, candidats pax et fret | 1 852 | Sonnet 5 / high | Le budget d'itérations A* est décidé **ici** (`OpexRailIterations`, `OpexRailDistanceForIterations`, `OpexDaysPerTile`, `OpexCompute*Distance`, `OpexRefreshEpochBounds`) avant toute économie : c'est ce modèle qui décide quels candidats existent. Puis `OpexBuildLineIndex`, `OpexPlaceJoinPax/Freight`, `OpexMakeCandidate`, `OpexTopK`, `OpexPaxCandidates`, `OpexFreightCandidates`. Plus gros fichier du dépôt, jamais relu depuis qu'il a doublé. |
| 5 | `candidates.nut:1853-3472` — assemblage, bandes, toute la famille route, subventions | 1 620 | Sonnet 5 / high | `OpexBuildCandidates` et `OpexBands` (assemblage et découpage en bandes), `OpexRoadPaxCandidates`, `OpexRoadFreightCandidates`, `OpexRoadExtensionCandidates`, `OpexRoadFeederCandidates`, `OpexBoostTownRating`, `OpexGenerateSubsidyCandidates` (C42). Interaction vivier ↔ `abandon_gen_filter` ↔ `abandon_cooldown_days`, tous deux actifs alors que le 09-06 recommandait de les remettre à 0 faute de banc isolé (constat G0, jamais tranché). |

### Couche 5 — sélection

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 6 | `projects.nut` | 2 149 | **Opus 5** / xhigh | Le nœud identifié par **trois audits indépendants** (étape 3 du 09-01, C31, revue du 09-06) : la borne du branch-and-bound n'est pas une borne supérieure valide (optimum non garanti), l'élection modale se fait avant le test de capital, le sac à dos optimise le **revenu** quand le code annonce le profit, la fenêtre `capitalCeiling` n'avance plus sous `portfolio_cache`. *Le code ne classe pas sur ce qu'il prétend classer* — et c'est le terrain sur lequel A1 doit être construit. `portfolio_v2` est seul chemin depuis le 09-11 (legacy supprimé) : vérifier qu'il ne reste pas de scorie. `biasPct` = 170 (rail) / 121 (route) dans `OpexProjectFinanceCapital` sont des **surcoûts réels mesurés**, pas des nombres magiques à supprimer. |

### Couche 6 — constructeurs

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 7 | `builder_rail.nut` | 2 144 | Sonnet 5 / xhigh | Plus gros fichier isolé. Recherche A* segmentée et reprenable (`rail_search_resumable`, `rail_micro_deadline`, `rail_segmented_search`, tous à 1) : vérifier qu'aucune tranche ne fuit d'itérations ni de budget calendaire. G6 ouvert : un `ABND`/`NOPA`/`DEAD` passe en phase `build` et attend un capital qui ne servira jamais, gelant tout nouveau candidat rail ; la branche « faible trésorerie » du plafond A* dynamique est du code mort (toujours appelée avec `false`). |
| 8 | `builder_air.nut` | 1 737 | **Opus 5** / high | **Le fait mesuré le plus gros et le moins expliqué du dépôt** : 1 396 des 1 590 `build_failed` sont `ERR_STATION_TOO_MANY_STATIONS_IN_TOWN` (erreur 771), et la sonde du 09-15 donne **291/291 avec zéro aéroport OpexAI dans la ville** — les deux slots sont pris par l'adversaire, ni nettoyage ni *distant join* ne débloquent. Par ailleurs G4 ouvert (le plan air fixe la demande à 22 % **avant** construction ; les arrêts `air_joined_stops` changent le captage réel après coup sans revenir dans le modèle, et leur coût est hors du ROI) et G7 ouvert (`OpexAirRollback` ignore A et ne protège pas B par `reuseB` : un échec sur un plan hub-à-hub peut **démolir un aéroport existant** et casser ses lignes). `airportDelayDays = 3,0` et `OpexAirCadenceCap` sont des approximations connues (C61), pas des capacités mesurées. |
| 9 | `builder_road.nut` | 1 606 | **Opus 5** / high | Le bug feeders bus du 09-15 (`OF_NONE` en ville et reprise de passagers au hub au retour) vient d'être corrigé ici sur **deux chemins** — construction et refleet : vérifier la symétrie, c'est le genre d'asymétrie qui survit à un correctif. `OpexRoadPhysicalVehicleCap = 2 × min(arrêts)` écrase la cible calculée et confond véhicules au terminus et en transit (chantier C61 connu, la suppression brute a déjà été réfutée par C50b). |
| 10 | `builder_water.nut`, `lib_water.nut`, **+ couture `ai/library`** | 1 474 | Sonnet 5 / medium | Chantier non fini et assumé — ses incohérences sont déjà listées dans `docs/taches.md`, inutile de les redécouvrir. **La couture est le vrai sujet de l'étape** : `MinchinWeb.Lakes` gèle 3/20 graines (C56), `WATER_LAKES_OPS = 50 000` est un premier jet jamais calibré (C57), le repli Manhattan n'est pas conservateur (il surestime le ROI), le BFS borné est réintroduit comme juge à la construction, et `lib_water.nut:306` porte le **seul `Valuate` du dépôt appelé avec une fonction Squirrel** — la faute n°1 des crashs NoAI (`excessive CPU usage in valuator function`), ici dans du code tiers importé. Grandes cartes 1024²/2048² jamais qualifiées en RAM ni en opcodes. |

### Couche 7 — orchestration

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 11 | `main.nut`, `persist.nut`, `scheduler.nut`, `scheduler_tasks.nut` | 1 713 | Sonnet 5 / high | Le contrat « nom de tâche » vit en **trois endroits** sans table nom→fonction : le littéral `_taskQueue` du constructeur (`main.nut:290-325`), la cascade de 15 `if` de `scheduler.nut`, les 15 `_dispatch*` de `scheduler_tasks.nut` ; un nom inconnu désactive silencieusement la tâche. `_dispatchTownGrowth` (`scheduler_tasks.nut:678`) appelle `_tryTownGrowth` dans **deux branches**, avec un `_runNextTask()` récursif intercalé — seul site de récursion de l'ordonnanceur. Budget d'opcodes non reportable (cause principale du sous-effectif de gares à l'étape 2 du 09-06 : revérifier après C20 et C36.1). **Trois familles de deadline non unifiées** : `dueCycle`, cadences calendaires internes aux dispatchs, budgets d'opcodes. **28 méthodes `OpexAI::` définies sans prototype** dans la classe, alors que 78 en ont un. Confronter `Save`/`Load`/`_reconcileAfterLoad` aux ~80 champs d'instance : le sous-ensemble sérialisé est-il suffisant ? |
| 12 | `events.nut`, `event_handlers.nut` | 1 200 | Sonnet 5 / high | G2 ouvert : `hadAbandons` ne se déclenche jamais avec les défauts (les vrais échecs n'alimentent pas `passDiscards`), et l'invalidation événementielle rafraîchit le catalogue mais **pas le portefeuille dérivé** dans le même mois. 14 types d'événement câblés en trois endroits (boucle `_processEvents`, handlers, prototypes). Trancher ici le cas `event_vehicle_autoreplaced` de l'étape 1 : adopté sans banc, et le code l'ignorerait. |

### Couche 8 — tâches métier

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 13 | `task_projects.nut`, `task_rail.nut` | 2 103 | **Opus 5** / high | `_tryBuildProjects` (≈ 600 l.) est le cœur d'exécution : lot dynamique (`_refreshDynamicBatch`, `portfolio_max_batch = 1`), `_railSearch` partagé avec l'étape 7, entonnoir C63 (`_c63RecordPassAndProbe`, `_recordMonthlyFunnelPass`). **C'est le code directement sous la priorité P1 (C63/C58, investissement et réinvestissement)** : les constats d'ici seront les plus immédiatement utiles au chantier en cours. Un bloc de ≈ 20 lignes (panneaux `IG|`, `FN|`, `IB|`) est dupliqué mot pour mot avec `scheduler_tasks.nut:286-308` — la duplication préexistait à C65, qui l'a répartie sur deux fichiers. |
| 14 | `task_air.nut`, `task_road.nut`, `task_feeders.nut` | 1 754 | Sonnet 5 / high | Dimensionnement et redimensionnement de flotte. G10 ouvert : une ligne aérienne déficitaire ne rejoint jamais le rebut normal, et la flotte aérienne est sous-comptée avant le premier rapport annuel. G5 ouvert dans sa forme courante : `rail_refleet = 1` mais le chemin qui rendrait `rail_expand` utile reste conditionné à `fleet_fix` (`info.nut:2316-2320` documente déjà une rectification — vérifier laquelle des deux lectures tient aujourd'hui). Rabattement pax et courrier, dont le correctif du 09-15 adopté malgré un banc négatif (étape 1, volet B). |
| 15 | `task_report.nut`, `task_town.nut`, `task_water.nut`, `ledgers.nut` | 1 740 | Sonnet 5 / high | Rapport annuel, ferraillage, purge des séries déficitaires, croissance urbaine, et les 26 registres C39→C60. **C56 — sur certaines graines l'IA cesse toute activité après 1970 sans erreur NoAI, cause non élucidée — se manifeste dans le cycle annuel.** Un constat qui explique cet arrêt silencieux vaut plus que tout le reste de l'étape. Vérifier aussi le coût des registres au défaut : une sonde en chemin chaud déplace la trajectoire mesurée (C63 : −37,6 % sur la graine 100 en smoke ON/OFF). |

### Couche 9 — transversale

| # | Objet | Modèle / effort | Enjeu |
|--:|---|---|---|
| 16 | Conformité NoAI et robustesse — dirigée par grep, tout le périmètre | Sonnet 5 / high | La checklist de `docs/00_conseils.md` (bancs d'essai Redirect Left : 90 % des crashs d'IA viennent de là) n'a **jamais été testée**, d'après le journal du 09-13 : `forbid_90_degree_turns` (crash ou boucle infinie sur beaucoup d'IA dès que l'option est cochée), `max_trains = 0` ou mode désactivé à l'initialisation (liste d'engins vide), **absence d'interrupteurs `enable_rail`/`enable_road`/`enable_air`/`enable_water`**, identifiants de cargo et de type de rail supposés (incompatibilité NewGRF), gares orphelines et voies en cul-de-sac après un échec à mi-chantier, **empreinte RAM de la VM Squirrel jamais mesurée** (5–10 Mo pour une IA saine comme AAAHogEx, > 50 Mo pour les mauvaises). Déjà vérifié en préparant ce plan : un seul `Valuate` à risque dans tout le dépôt, et il est dans le code tiers (étape 10) — ce point-là est à confirmer, pas à redécouvrir. Rappel : philosophie « armes égales », aucun bridage qui handicaperait OpexAI face à AAAHogEx. |

### Couche 10 — harnais de mesure

`sweeps/` compte 196 scripts et 45 134 lignes ; seuls les scripts **qui arbitrent encore des
décisions** sont dans le périmètre (5 635 l.). Le reste est de l'archive d'expérience.

| # | Fichiers | L. | Modèle / effort | Enjeu |
|--:|---|--:|---|---|
| 17 | `bench_1v1_5y_20seeds.py`, `game_health.py`, `smoke_test.py` | 2 238 | **Opus 5** / xhigh | **C'est ici que le projet se fait le plus mal.** `extract_company_record` compte les entrées `VEHS` par propriétaire **sans filtrer les composants** (wagons, ombres, rotors) : c'est ce qui a produit puis fait retirer le diagnostic « 93 % de rendement par véhicule, donc presque uniquement du volume ». `vehicle_breakdown` et `physical_telemetry` ont le même défaut malgré le nom `primary_vehicles_by_mode`. La revue du 09-14 a rouvert 4 faux positifs de santé (`annotate_summary` réhabilitant un `run_ok=False`, crash et timeout moteur perdus, compagnie disparue au dernier checkpoint, `earning_without_expansion` trop permissif). `expected_last_year` n'est pas renseigné et la sortie du moteur n'est pas transmise au contrôle d'échec d'AAAHogEx. C'est le livrable P0 (C66) : **toute conclusion économique du projet passe par ces 2 238 lignes.** |
| 18 | `bench_v2.py`, `bench.py`, `head_to_head.py`, `diag_c63_c58.py` | 2 159 | Sonnet 5 / high | Le banc officiel 20 × 10 apparié lui-même, et le diagnostic qui porte la priorité P1. Vérifier l'appariement par graine, le **test des signes** (≥ 15/20, p < 0,05, les ex æquo signifiant « le drapeau n'a pas joué » et jamais une victoire), et l'**épinglage explicite de tous les réglages dans chaque bras, y compris le bras de contrôle** — constat G0 du 09-06, jamais clos : un bras qui hérite des défauts courants ne mesure pas ce qu'il annonce. Vérifier aussi si un coût d'opcodes ou une densité profit/opcode est produit (constat G0bis : la métrique nord du projet n'apparaît dans aucun JSON de banc). |
| 19 | `diag_1v1_shared_monthly.py` | 1 238 | Sonnet 5 / high | Enregistreur mensuel partagé écrit le 09-13 (C66.2), jamais relu. Vérifier le coût de la sonde au défaut et son effet sur la trajectoire mesurée, ainsi que la qualification des compteurs (mode eau explicitement non qualifié dans la fixture C66). |

### Clôture

| # | Objet | Modèle / effort |
|--:|---|---|
| 20 | **Synthèse.** Regrouper les constats des 19 étapes **par mécanisme** (pas un correctif par constat), trancher gravité et ordre, et produire `docs/revue_code_2026-09-15_correctifs.md` sur le modèle du 09-06 : tiers, groupes, modèle et effort de **correction**, greffes opportunistes depuis `docs/taches.md`. Solder au passage les 12 groupes G0–G12 du 09-06 : lesquels sont fermés, lesquels sont encore ouverts, lesquels sont devenus caducs. | **Opus 5** / high |

**Total** : 20 étapes, 28 868 lignes Squirrel + 5 635 lignes Python. Couverture vérifiée par
recomptage : chaque `.nut` du répertoire apparaît **exactement une fois**, la somme des étapes
tombe sur 28 868 au fichier près, et aucun fichier n'est oublié ni compté deux fois.

## Sortie attendue par étape

Un fichier `docs/revue/2026-09-15_etape_NN_<nom>.md` — jamais un ajout à un fichier partagé, c'est
la règle de quota la plus importante du lot. Squelettes déjà créés, il n'y a qu'à les remplir.

```
# Étape NN — <nom>        (SHA revu : <sha>)

## Constats
### NN.1 — <titre>        [gravité : P1 | P2 | P3]
`fichier:ligne` — ce que le code fait · ce qu'il prétend faire · conséquence observable.

## Vérifié, n'est PAS un bug
## Hors périmètre, à relire ailleurs
```

Rien n'est corrigé au passage, dans aucune étape. Une fois les 20 étapes closes, trancher ensemble
ce qui passe en correctif — probablement plusieurs tâches numérotées à ajouter à `docs/taches.md`.

## Note sur le choix des modèles

Repère du 09-06, inchangé : la revue fichier par fichier réussit bien à **Sonnet 5** (bug du budget
d'opcodes, `rail_refleet` inatteignable, les quatre soupçons du sac à dos). Le seul type de tâche
où Sonnet avait laissé passer quelque chose est **l'audit statistique d'adoption** (C31, qui a
rattrapé C29.3), confié à **Opus 5**. D'où la répartition : Opus sur l'étape 1 (volet B), sur les
deux étapes à plus fort enjeu économique (6 et 13), sur les deux constructeurs qui portent des
faits mesurés inexpliqués (8 et 9), sur le harnais (17) et sur la synthèse (20) ; Sonnet ailleurs,
avec l'effort relevé à `xhigh` sur les deux plus gros fichiers isolés (7) et sur le harnais.

Sur une revue croisée avec Codex, la conclusion du 09-06 tient : pas de raison solide de basculer
tout le lot, mais là où l'enjeu est le plus fort (ici les étapes 1, 8 et 17), faire tourner Codex
**en plus** de Claude plutôt qu'à sa place — les angles morts des deux familles ne se recouvrent
pas, et c'est le seul point de la littérature qui tienne au-delà du marketing.
