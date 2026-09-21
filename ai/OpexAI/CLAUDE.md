# OpexAI — contexte pour la revue de code

## Quoi
`OpexAI` est une IA de jeu OpenTTD (framework NoAI), multimodale (rail, route, air, eau).
Objectif du script (`info.nut`) : "meilleur ROI par origine/destination, puis revenu maximisé
sous contraintes de capital et d'opcodes."

## Le but : battre AAAHogEx
AAAHogEx est l'IA adverse utilisée comme arbitre externe de toute décision : en cas de désaccord
entre un raisonnement interne et le résultat d'un banc contre AAAHogEx, le banc gagne. Toute la
logique de scoring interne (profit/opcode, ROI) n'est qu'une heuristique d'allocation ; la
métrique qui compte est la comparaison directe (`company_value`, `profit_year`) sur carte
partagée.

État mesuré le plus récent (référence 1v1 du 2026-09-13, carte partagée, 20 graines × 5 ans,
`results/bench_1v1_5y_20seeds_reference.json`) : AAAHogEx gagne **0/20 pour OpexAI** sur toutes
les métriques — valeur −71,6 %, profit annuel −83,1 %, 564 véhicules en moyenne contre 102.
À 10 ans (duel C42, 2026-09-11) : 37,79 M£ / 10,26 M£ / 1 077 véhicules contre 5,67 M£ /
1,24 M£ / 158. Le rendement par véhicule est à 93 % de celui d'AAAHogEx : **l'écart est du
volume** (véhicules, gares), presque entièrement.
Ne pas citer de chiffre antérieur au 2026-09-09 : ces résultats sont archivés et ne font plus foi
(voir `docs/taches.md`).

## Carte des modules (27 266 lignes, 34 fichiers)

C65 (2026-09-13) : découpage complet. Passes 1–2 : déplacement pur, bit-identique.
Passe 3 : `_processEvents` / `_runNextTask` dispatchent vers un handler par type
(`event_handlers.nut`, `scheduler_tasks.nut`) — un appel de plus par événement/tâche,
banc 20×10 : 12 ex æquo, 4/4 sur le reste, moyenne −0,43 %, pas de régression
systématique. Les `const` restent dans `main.nut`. Les méthodes `function OpexAI::x()`
sont dans le **second** bloc `require`, après la classe. `globals_pre.nut` avant
budget/catalog ; `globals_post.nut` après `builder_road.nut`.

| Fichier | Rôle |
|---|---|
| `info.nut` (2 643) | `AIInfo` : déclaration de tous les réglages et drapeaux d'expérience |
| `candidates.nut` (3 282) | Génération des candidats de ligne (rail, route, air, fret) et modèle de coût A* |
| `builder_rail.nut` (2 144) | Construction ferroviaire, recherche segmentée/reprenable |
| `projects.nut` (1 914) | Sélection du portefeuille (`portfolio_v2`), financement (`OpexProjectFinanceCapital`) |
| `builder_air.nut` (1 727) | Aéroports, modèle de rotation (`OpexAirTripModel`), plafond de cadence |
| `builder_road.nut` (1 388) | Lignes routières, plafond physique de véhicules |
| `task_rail.nut` (1 102) | Construction / expansion / A* rail, réparation C41 |
| `catalog.nut` (884) | Catalogue moteurs/cargos/industries |
| `builder_water.nut` (846), `lib_water.nut` (610) | Mode eau (chantier non fini, voir `docs/taches.md`) |
| `task_projects.nut` (846) | Sac à dos, batch dynamique, `_tryBuildProjects` |
| `event_handlers.nut` (822) | Un handler par type d'événement (`_onVehicleCrashed`, …) |
| `task_air.nut` (737) | Construction et flotte aériennes |
| `ledgers.nut` (707) | Registres annuels C39/C41/C48/C49/C50/C52/C54/C55/C60 |
| `economy.nut` (704) | Scoring économique (ROI, projections) |
| `scheduler_tasks.nut` (703) | Un dispatch par tache de file (`_dispatchCatalog`, …) |
| `tension.nut` (689) | Score de tension capacité/attente |
| `task_report.nut` (666) | Rapport annuel, ferraillage |
| `main.nut` (540) | `const`, classe `OpexAI`, `Start()` (file, emprunt, boucle) |
| `task_road.nut` (491) | Construction et refleet routiers |
| `probes.nut` (447) | `OpexSign`, `OpexDecide`, journaux de sondes |
| `lines.nut` (429) | Identité de ligne, jointure, abandon |
| `globals_pre.nut` (414) | Globales du bloc avant `require(budget/catalog/…)` |
| `events.nut` (357) | `_processEvents` (dispatch), `_markDirty`, sonde C52 |
| `settings.nut` (336) | `OpexLoadSettings()` : lecture unique des 213 `GetSetting` |
| `globals_post.nut` (269) | Globales du bloc après `builder_road.nut` |
| `scheduler.nut` (241) | `_runNextTask` (round-robin + dispatch) |
| `persist.nut` (219) | `Save` / `Load` / `_reconcileAfterLoad` |
| `task_town.nut` (213) | Croissance urbaine |
| `spatial.nut` (183) | Grille spatiale pour les candidats fret (C46) |
| `capital.nut` (136) | `OpexCashReserve`, `OpexAvailableCapital`, emprunt |
| `task_water.nut` (103) | Construction et refleet eau |
| `budget.nut` (92) | Réserve de trésorerie |

## Architecture : le budget d'opcodes est une ressource de flux, pas un stock
Chaque tick de jeu accorde un budget d'opcodes fixe avant suspension du script
(`script_max_opcode_till_suspend`, de l'ordre de 10 000). Ce budget ne se cumule pas d'un tick à
l'autre : tout calcul long doit donc pouvoir être découpé et repris plutôt qu'exécuté d'un bloc.
Deux implémentations concrètes de ce principe, déjà en production (pas un plan futur) :
- **Ordonnanceur de micro-tâches** (`scheduler.nut`, file construite dans `main.nut`) :
  `_taskQueue` est une liste de tâches nommées (catalogue, rapport, mise à la casse,
  construction eau/route/rail/signalisation...) avec `dueCycle` et `enabled` ; `_taskCursor`
  fait tourner l'exécution en round-robin, persisté à la sauvegarde.
- **Recherche de chemin ferroviaire segmentée et reprenable** (`builder_rail.nut`) :
  `rail_search_resumable`, `rail_micro_deadline`, `rail_segmented_search` (tous à défaut 1,
  adoptés) découpent l'A* en tranches de `RAIL_SEARCH_SLICE` itérations avec un point de reprise
  explicite plutôt qu'un recalcul.

Le pipeline de décision (sélection des lignes à construire) : `candidates.nut` génère les
candidats → `economy.nut` les score en ROI → `projects.nut` sélectionne le portefeuille à
construire (`portfolio_v2`, seul chemin depuis le 2026-09-11 — le legacy knapsack a été
supprimé, pas de branche morte à unifier).

## Conventions du code
- **Réglages** : déclarés dans `info.nut` (`AddSetting`, les quatre `*_value` toujours égaux — pas
  de niveau de difficulté), lus **une seule fois** dans `settings.nut::OpexLoadSettings()` via
  `AIController.GetSetting` vers des globales en MAJUSCULES, appelé depuis `Start()`. Un drapeau
  `cNN_*` renvoie à la fiche C-NN de `docs/taches.md`.
- **Mesure** : les panneaux `OpexSign(...)` (préfixes `AC|`, `RC|`, etc.) sont le canal de mesure
  des bancs ; `OpexDecide(kind, fields)` (`probes.nut`) est le journal de décision structuré, gardé
  par `decision_log` ou une sonde dédiée — coût nul au défaut.
- **Cycle de validation d'un changement de comportement** : sonde passive → diagnostic 5 graines ×
  6 ans → banc officiel 20 graines × 10 ans apparié, lu au **test des signes d'abord** (≥ 15/20,
  p < 0,05), moyennes ensuite. Un défaut ne change jamais sur moins que ça. Deux bras identiques
  sur une graine (ex æquo) signifient « le drapeau n'a pas joué », pas une victoire.
- Après toute modification d'un `.nut` : smoke test (2 graines × 3 ans) **avant** commit — une
  erreur de compilation Squirrel tue l'IA au démarrage presque en silence (`company_value = 1`,
  zéro panneau).

## Pièges Squirrel / NoAI propres à cet environnement
- Une closure imbriquée (`local f = function(...) {...}`) **ne capture pas** les `local` de la
  fonction englobante : tout ce dont elle a besoin lui est passé en paramètre ou lu via `this.*`.
  Ne pas « simplifier » en capture de closure — ça compile puis échoue à l'exécution.
- `const` n'accepte qu'un **littéral scalaire** (ni référence à une autre constante, ni
  expression) : les valeurs dupliquées en dur avec un commentaire d'origine sont voulues.
- `clone` et `base` sont des mots réservés ; les utiliser comme identifiant casse la compilation
  du fichier entier.
- `AIAccounting` comptabilise aussi le coût **simulé** des commandes jouées sous `AITestMode` :
  un `AIAccounting()` imbriqué autour d'un sondage en mode test est un bouclier délibéré (le
  destructeur imbriqué jette son compteur), pas une redondance.
- `AITown.GetRating` renvoie un enum (`TOWN_RATING_*`, 0..8), pas la note brute −1000..1000.

## Ce qui ressemble à un bug mais n'en est pas un
- La plupart des réglages de `info.nut` sont des **drapeaux d'expérience à défaut 0/false/off** :
  du code vivant mais volontairement inerte (hypothèse déjà banquée et rejetée, ou pas encore
  banquée). Vérifier la valeur par défaut avant de signaler "code mort" ou "flag jamais activé".
  Exemples au 2026-09-13 : `c50b_rail_backlog_relax`
  (banqué, inerte), `air_cadence_cap_adaptive` (banqué le 2026-09-13 : 9 V / 2 D / 9 ex æquo,
  non adoptable, son seuil constant est en cours de remplacement — fiche C64), tous les
  `*_cost_probe` (mesure seule).
- `OpexProjectFinanceCapital` (`projects.nut`) applique `biasPct` = 170 (rail) / 121 (route) :
  ce sont des **surcoûts réels mesurés** (terrain non pricé par le modèle de coût), pas des nombres
  magiques à supprimer — leur remplacement par un devis physique est un chantier ouvert.
- `debug_signs=1` par défaut n'est pas un oubli de debug : c'est la seule source de mesure pour
  tous les bancs `sweeps/*.py`. Il ne doit être mis à 0 que pour une partie réelle avec des
  humains.
- Philosophie "armes égales" : ne jamais proposer de bridage ou de simplification qui
  handicaperait OpexAI par rapport à AAAHogEx (qui, lui, ne se bride jamais) — un déséquilibre
  involontaire invaliderait tout le banc.
- `GetAPIVersion()` déclare "15", aligné sur la plateforme de banc OpenTTD 15.3 (C62).

## Chantiers ouverts à connaître avant de qualifier un finding
- **C61** : les plafonds de flotte air (`OpexAirCadenceCap`, délai fixe de 3 jours dans
  `OpexAirTripModel`) et route (`OpexRoadPhysicalVehicleCap = 2 × min(arrêts)`) sont des
  approximations grossières **connues** ; la cible est un modèle temporel partagé, pas une
  suppression brute (déjà réfutée par C50b).
- **C56** : sur certaines graines l'IA cesse toute activité après 1970 sans erreur NoAI ; cause non
  élucidée — un finding qui explique un arrêt silencieux du cycle annuel vaut de l'or.
- **Mode eau** : chantier explicitement non fini (`builder_water.nut`, `lib_water.nut`) ; ses
  incohérences sont listées dans `docs/taches.md`, pas besoin de les redécouvrir.

## Pour aller plus loin
L'historique complet des décisions, mesures et fiches techniques vit dans `docs/taches.md`
(journal continu) — un humain doit le consulter avant d'agir sur un finding, même si cet outil de
revue ne le lira pas automatiquement. Les schémas d'architecture (couches, ordre de chargement,
cycle d'exécution, dispatch des tâches et des événements, pipeline de décision, constructeurs,
matrice des dépendances) sont dans `docs/architecture_opexai.md`.
