# OpexAI — contexte pour la revue de code

Consignes réconciliées le **2026-09-30** par lecture statique. Les chemins ci-dessous sont
relatifs à la racine du dépôt, sauf les noms de modules `.nut`, relatifs à `ai/OpexAI/`.
`AGENTS.md` fait autorité pour les méthodes et `docs/taches.md` pour le travail restant.
Ce fichier ne constitue ni un second backlog ni une qualification économique du code courant.

## Quoi
`OpexAI` est une IA de jeu OpenTTD (framework NoAI), multimodale (rail, route, air, eau).
Le portefeuille courant classe les projets par `fundScore`, fondé sur le profit attendu,
la calibration par mode et le dénominateur C69, sous contrainte de capital. La description
historique d'`info.nut` parlant de revenu ne suffit pas à définir ce contrat.

## Le but : battre AAAHogEx
AAAHogEx est l'IA adverse utilisée comme arbitre externe de toute décision : en cas de désaccord
entre un raisonnement interne et le résultat d'un banc contre AAAHogEx, le banc gagne. Toute la
logique de scoring interne (profit/opcode, ROI) n'est qu'une heuristique d'allocation ; la
métrique qui compte est la comparaison directe (`company_value`, `profit_year`) sur carte
partagée.

Les mesures historiques et dérogations sont dans
[la synthèse des décisions](../../docs/journaux/synthese_decisions_2026-09-30.md),
pas dans ces instructions. Ne pas réutiliser les comptes `VEHS` bruts ni le ratio
erroné « rendement à 93 % ». Les résultats antérieurs au 9 septembre ne font plus foi.

## Carte des modules

Consulter [l'architecture courante](../../docs/architecture_courante.md) : responsabilités
et ordre de chargement, sans les anciennes tailles de fichiers. `main.nut` reste
la source de vérité des `import`/`require`. Les méthodes `OpexAI::...` se chargent
après la classe ; `globals_pre.nut` avant les helpers, `globals_post.nut` après les builders.

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
  les globales `RAIL_SEARCH_RESUMABLE`, `RAIL_MICRO_DEADLINE`, `RAIL_SEGMENTED_SEARCH`,
  désormais chargées par `policy_rail`, découpent l'A* en tranches avec un point de reprise
  explicite. Les anciens réglages individuels ne sont plus des options publiques.

Le pipeline de décision (sélection des lignes à construire) : `candidates.nut` génère les
candidats → `economy.nut` les score en ROI → `projects.nut` sélectionne le portefeuille à
construire (portefeuille v2, seul chemin depuis le 2026-09-11 — le legacy knapsack a été
supprimé, pas de branche morte à unifier).

## Conventions du code
- **Réglages** : déclarés dans `info.nut` (`AddSetting`, les quatre `*_value` toujours égaux — pas
  de niveau de difficulté), lus **une seule fois** dans `settings.nut::OpexLoadSettings()` via
  `AIController.GetSetting` vers des globales en MAJUSCULES, appelé depuis `Start()`. Un drapeau
  `cNN_*` renvoie à la fiche C-NN de `docs/taches.md`.
- **Mesure** : les panneaux `OpexSign(...)` (préfixes `AC|`, `RC|`, etc.) sont le canal de mesure
  des bancs ; `OpexDecide(kind, fields)` (`probes.nut`) est le journal de décision structuré, gardé
  par `decision_log` ou une sonde dédiée — coût nul au défaut.
- **Validation** : appliquer `AGENTS.md` §4, source unique du protocole. Après une modification
  `.nut`, smoke de compilation/exécution **1 graine × 1 an**, puis diagnostic causal **5×6**
  si le comportement change, et qualification **20×10** avant adoption ordinaire.
  Les optimisations d'opcodes ont une règle de neutralité dédiée ; les dérogations utilisateur
  restent explicitement tracées et ne changent pas le verdict statistique. Un ex æquo n'est
  pas une victoire, ni à lui seul la preuve qu'un drapeau n'a pas été exposé.
- **Défauts et bancs automatiques** : appliquer `AGENTS.md` §4.1. Pour un changement
  de défaut demandé, préférer `qualify.yml` avec un
  [plan pré-enregistré](../../qualifications/README.md), puis suivre ses portes et
  ses artefacts. `bench.yml` reste le parcours manuel `paired/smoke`, puis
  `paired/diagnostic`, puis `paired/adoption` si les portes précédentes sont franchies.
  Garder l'ancien défaut pendant les essais ; ne pas attendre une nouvelle demande
  de lancement lorsque accès/publication/budget sont disponibles. Un blocage d'accès
  ou de publication doit être signalé, jamais contourné par un push implicite.
  Lire les artefacts et le verdict économique, pas seulement la couleur du job ou
  le pourcentage Opex/AAAHogEx. La règle opcodes et les interdictions de chantier
  restent applicables. Guide d'exécution : `docs/bancs_github.md`.

## Pièges de mesure (bancs)
- **La ligne `[ai_players]` d'`openttd.cfg` est lue sur ~1 024 caractères.** Un harnais qui passe
  toutes les valeurs de réglage fait ignorer en silence ceux de fin d'ordre alphabétique (mesuré le
  2026-09-21 : `town_growth=0` lu 1). `bench_v2` et le harnais C66 ne passent plus que les écarts au
  défaut ; tout nouveau harnais doit faire de même.
- **Le solo est déterministe au bit près, le duel ne l'est pas** (jusqu'à 18 % d'écart d'un rejeu
  à l'autre). Un 5×6 solo positif **ne prédit pas** le 20×10 duel (trois échecs le 2026-09-21) :
  il sert à vérifier un mécanisme, pas à filtrer une idée.
- **Tout ajout de code décale les opcodes** et la trajectoire d'une partie (effet chaotique) :
  une variante « inerte » au défaut n'est pas identique au bit près à `master` ; l'identité se
  vérifie entre deux bras du **même** code.
- **Les bancs démarrent en 1970 et ne rechargent jamais** : tester explicitement le rechargement
  (`sweeps/save_load_roundtrip.py`) et un autre millésime de départ quand un état ou une date
  intervient (`docs/19_rechargement_partie.md`).
- **Dans la sauvegarde, une référence d'objet vaut identifiant + 1** (0 = aucune) : la ville d'une
  gare décodée par `bench_1v1_5y_20seeds.py` (`town`, `town_ids`) est l'identifiant de l'API **+ 1**.
  Comparer des lignes de la sauvegarde entre elles est sans risque ; les croiser avec un identifiant
  journalisé par l'IA exige le −1 (C78 étape 1 invalidée par ce décalage le 2026-09-22 ;
  `diag_b9_air_catchment.py` et `diag_c78_lines_vs_aaa.py` le corrigent).

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
  Exemples : les `*_cost_probe` (mesure seule).
- `OpexProjectFinanceCapital` (`projects.nut`) lit `rail_finance_bias_pct`, **100 par défaut**
  depuis la décision du 26 septembre ; la route conserve 121. Ne pas confondre ce facteur de
  financement avec `RAIL_TERRAIN_FACTOR=170`, déjà inclus dans l'estimation du capital rail.
  Restaurer 170 en financement réintroduirait une majoration supprimée ; consulter C67.
- `debug_signs=1` par défaut n'est pas un oubli de debug : c'est la seule source de mesure pour
  tous les bancs `sweeps/*.py`. Il ne doit être mis à 0 que pour une partie réelle avec des
  humains.
- Philosophie "armes égales" : ne jamais proposer de bridage ou de simplification qui
  handicaperait OpexAI par rapport à AAAHogEx (qui, lui, ne se bride jamais) — un déséquilibre
  involontaire invaliderait tout le banc.
- `OPEX_START_YEAR` (posé dans `Start()` depuis `_startYear`) sert de base aux calculs de F et τ
  de C69/C75 : ne pas le remplacer par 1970 (défaut corrigé le 2026-09-21). Les dates C69/C75 sont
  sauvegardées exprès : sans elles, K_dec est multiplié par ~14 après un chargement.
- Dans `_reconcileAfterLoad`, `OpexC70RecomputeFactors` / `OpexC82RecomputeFactors` sont appelés
  **après** `this._lines = liveLines` : plus haut, la liste est encore vide et tous les facteurs
  retombaient à 1 (défaut corrigé le 2026-09-22, `docs/19_rechargement_partie.md` §7).
- Les sondes du 2026-09-21 (C69, C72, C73, C76) ont réécrit des conditions de filtrage en blocs
  avec compteurs (`builder_air.nut`, `candidates.nut`, `task_air.nut`, `builder_water.nut`) ; leur
  équivalence avec l'original a été vérifiée à la lecture et figure à l'étape 2 de la revue
  `docs/revue_code_2026-09-21_plan.md`.
- `GetAPIVersion()` déclare "15", aligné sur la plateforme de banc OpenTTD 15.3 (C62).

## Chantiers ouverts à connaître avant de qualifier un finding
- **C61** : les plafonds de flotte air (`OpexAirCadenceCap`, délai legacy de 3 jours dans
  `OpexAirTripModel`, distinct des chemins C115/C121) et route (`OpexRoadPhysicalVehicleCap = 2 × min(arrêts)`) sont des
  approximations grossières **connues** ; la cible est un modèle temporel partagé, pas une
  suppression brute (déjà réfutée par C50b).
- **C56 (clos)** : les graines 2026, 1337 et 1024 gelaient dans la phase eau (`FindPath` de
  MinchinWeb Lakes, budget compté en itérations alors qu'une itération n'est pas bornée). Corrigé
  le 2026-09-11 par `water_lakes_ops_budget` (réglage historique, retiré avec Lakes le 21) ; vérifié le 2026-09-23 :
  ces graines jouent normalement dans les 20×10 duel. Leçon toujours valable : un arrêt silencieux
  (`run_ok` vrai, aucune erreur NoAI) se cherche par l'année de fin et les jalons de phase.
- **Goulot du volume** : les mesures historiques sont dans `docs/16_bilan_volume.md`.
  `c76_regen_targeted`, `town_growth_plan_memo`, `c80_mode_regen` et `c80_air_hub_index`
  sont **actifs par défaut**. Les workers rail/ville et de stock A* restent expérimentaux,
  défaut 0 ; leur pile a déjà été mesurée. Ne pas relancer leurs qualifications comme si elles
  n'avaient pas eu lieu : consulter les décisions et conditions de reprise de `docs/taches.md`.
- **C75 a montré** qu'ajouter du volume ne paie pas si le vivier ne contient pas mieux : +42
  véhicules pour +23 k£/an (`docs/16_bilan_volume.md` §9). La qualité des candidats face à
  AAAHogEx (génération, évaluation, exploitation) reste la question ouverte principale.
- **Mode eau** : le builder courant utilise un BFS borné ; `lib_water.nut` et Lakes ont été
  retirés. C67.3 à C67.6 sont livrés (`terrain_map.nut`, `water_graph.nut`, `task_terrain.nut`),
  sans consommateur métier exposé aux décisions. Consulter le reliquat dans `docs/taches.md`.

## Pour aller plus loin
Le travail restant et les décisions courantes sont dans `docs/taches.md` ; l'historique est dans
les journaux et fiches liés. Les consulter avant d'agir sur un finding. Les schémas d'architecture (couches, ordre de chargement,
cycle d'exécution, dispatch des tâches et des événements, pipeline de décision, constructeurs,
matrice des dépendances) historiques sont dans `docs/architecture_opexai.md` ;
commencer par `docs/architecture_courante.md` et `docs/README.md`.
