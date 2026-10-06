# Revue OpexAI — plan fractionné du 26 septembre 2026

**Statut au 30 septembre : plan historique.** Les mentions « aucun lot exécuté »
et la discipline ci-dessous décrivent la demande du 26, pas la file actuelle.
Pour les constats consolidés et les correctifs locaux, lire la
[revue du 30](revue_code_2026-09-30.md) ; seul [taches.md](taches.md) fixe la suite.

## Périmètre et point de départ

Préparation demandée par l'utilisateur pour éviter de consommer le quota en une seule passe.
Référence de préparation : `ed8fc1388c83077f6ffc80419fb7b6efa4f87f7d`, dépôt propre.
**La préparation est terminée ; aucun lot de revue ci-dessous n'a encore été exécuté.**
La revue porte sur le code courant d'OpexAI et ses contrats de mesure, pas seulement sur un diff.
Les changements récents et les chemins actifs passent en premier. Aucun correctif pendant la revue.
`docs/taches.md` reste la seule liste autoritaire du travail restant ; ce document en détaille
uniquement la méthode et le découpage.

## Discipline de consommation

- **Un seul lot par demande, puis arrêt avec un rapport enregistré.** Aucun enchaînement
  automatique, aucune campagne ni agent parallèle. Une nouvelle conversation est préférable
  pour le lot suivant, avec le présent plan et le rapport précédent comme points de reprise.
- Viser **800 à 1 200 lignes de source lues par passe**, plafond opérationnel **1 500**,
  dépendances et tests compris. Ce bornage limite le contexte, sans garantir un quota exact.
  Lire les fonctions complètes utiles, pas tous les fichiers indiqués dans le tableau.
- Au début du lot, sélectionner les fonctions et leurs appelants directs. Si le périmètre
  dépasse le plafond, le subdiviser en `03a`, `03b`, etc. ; consigner la suite et s'arrêter.
  Ne jamais déclarer un lot complet lorsque des branches utiles restent non lues.
- Lire l'état courant et la ligne pertinente de `docs/taches.md`, puis seulement les sections
  d'historique nécessaires. Éviter les journaux, gros JSON et bibliothèques lus en entier.
- Rapport court : constats démontrés, couverture précise, limites et reprise. Ne pas recopier
  le code ou l'historique. Un doute non résolu reste une hypothèse, pas un bug.

## Lots, dans l'ordre proposé

Les fichiers `.nut` sont relatifs à `ai/OpexAI/`. Les groupes sont des zones à découper par
fonctions, **pas une consigne de lecture intégrale**. Les tests cités sont des points d'entrée
existants à inspecter ; leur présence ne prouve ni leur pertinence ni la compilation Squirrel.

| Lot | Zone et fichiers d'entrée | Contrat à examiner / tests à sélectionner |
|---|---|---|
| 01 | Chargement et réglages : `main`, `globals_pre`, `globals_post`, `info`, `settings` | Ordre des définitions, bornes/défauts/chargement/usages des réglages récents ; distinguer code actif, expérimental et documentation périmée. Produire la carte des fonctions des lots suivants. |
| 02 | Admission et capital : `projects`, `capital`, `budget`, `tension` | Classement, finançabilité, caisse réservée, exemption flotte et C75 bis une fois par passe ; `test_c75_kpass_bypass.py`, `test_c75bis_v89_railfactor.py`, `test_b6_portfolio_causality.py`. |
| 03 | Cycle du portefeuille : `task_projects`, `projects`, `candidates` | Revalidation après construction, candidats périmés, invalidation et régénération C76/C77 ; `test_p2_lifecycle.py`, `test_p2bis_reconciliation.py`, `test_c45_subsidy_persistence.py`. |
| 04 | Ordonnanceur : `scheduler`, `scheduler_tasks`, `orchestrator`, boucle de `main` | Progression des tâches, verrous, reprises, travail réellement dû, budgets et suspensions ; `test_scheduler_task_contract.py`, `test_p5_preplan.py`. |
| 05 | Rail, exécution : `task_rail`, `builder_rail` | Recherche → construction → ordres, abandon et nettoyage des échecs partiels, V89 ; `test_v89_rail_throughput.py`, `test_review_residual_contracts.py`. |
| 06 | Rail, recherche : `pathfinder_v90/` et raccordement du builder | Tas/A*, état entre tranches, caches, poids V91 et mode de comparaison ; `test_v90_fast_pathfinder.py`, `test_v91_astar_weight.py`. Vérifier dépendances/licences ; ne pas remplacer le modèle de vitesse C41. |
| 07 | AIR, plans et sites : fonctions concernées de `builder_air`, `spatial`, `catalog` | Demande, bassins, sites V94, slots et portée des gardes C83 ; `test_v94_air_site_list.py`, `test_c83_fixes.py`, `test_b9_air_catchment.py`. Consulter la revue AIR du 24 avant toute reprise d'un constat. |
| 08 | AIR, construction et flotte : `builder_air`, `task_air`, `lines` | Achat/refit/ordres, réutilisation d'aéroport, rollback, flotte cible et références invalides ; `test_v86_hubhub_contract.py`, `test_v92_air_service.py`, `test_review_residual_contracts.py`. |
| 09 | Route et croissance : `builder_road`, `task_road`, `task_town` | Construction partielle, véhicules démarrés, nettoyage, C87 et villes abandonnées ; `test_b3_road_fleet_targets.py`, `test_review_residual_contracts.py`. |
| 10 | Eau et terrain : `builder_water`, `task_water`, `terrain_map`, `water_graph`, `task_terrain` | BFS borné, exact/inconnu, invalidation et reprises C67 ; `test_b7_water_guards.py`, `test_c67_water.py`, `test_c67_terrain.py`. C67.3–6 existent ; ne pas supposer un consommateur métier actif. |
| 11 | Chaînes industrielles V88 : fonctions dédiées de `projects`, `task_projects`, `task_rail` | Identité de chaîne, étapes, verrou rail, interruption et livraison ; `test_v88_goods_chain.py`, `test_v88_analyse.py`. Garder la qualification économique distincte de la correction logique. |
| 12 | Événements et fin de vie : `events`, `event_handlers`, `lines` | Destruction/vente/fermeture, références obsolètes, subventions, réveils et invalidations ; `test_b8_scrap_lifecycle.py`, `test_c45_subsidy_persistence.py`. |
| 13 | Persistance transversale : `persist` et champs recensés dans les lots précédents | Save/Load/réconciliation, tâches interrompues, caches reconstructibles et état décisionnel ; `test_b5_rail_persistence.py`, `test_c69_reload_contract.py`, protocole `save_load_roundtrip.py`. |
| 14 | Modèles économiques : `economy`, fonctions économiques des builders, `catalog`, `task_report` | Unités, signes, amortissement, cargos, durée et calibration ; vérifier les contrats entre prédiction et décision, sans conclure à un gain économique par lecture. |
| 15 | Sondes : `probes`, `ledgers`, émetteurs des tâches | Garde effective sonde=0, attribution, longueur des signes et coût perturbateur ; `test_sched_idle.py`, `test_m1_measurement_truth.py`, `test_v95_air_post73_probe.py`. |
| 16 | Harnais : `sweeps/run_c66_reference.py`, `campaign_freeze.py`, `bench_1v1_5y_20seeds.py`, `bench_v2.py` | Gel, appariement, réglages, contrat du processeur et limites Docker ; `test_campaign_freeze.py` et selftests pertinents. |
| 17 | Décodage et preuve : `sweeps/physical_counters.py`, `game_health.py`, analyses concernées | Propriétaire, trimestre clos, inconnus, horizon, santé et agrégation ; tests homonymes et `test_review_evidence.py`. Lire seulement les preuves nécessaires aux constats. |
| 18 | Réconciliation finale des rapports | Dédupliquer, revérifier les constats sur le HEAD final, lister couvert/non couvert et proposer les corrections avec leur validation. Actualiser les statuts dans `docs/taches.md`. |

## Protocole de chaque passe

1. Lire les instructions applicables ; enregistrer HEAD, état Git et diff local. Préserver les
   changements de l'utilisateur. Si HEAD a changé depuis la passe précédente, examiner le diff
   des seules fonctions concernées et noter la référence réellement revue.
2. Confronter les anciens constats au code actuel. Sources historiques :
   [réconciliation du 22](revue_code_2026-09-22_reconciliation_courante.md),
   [revue AIR du 24](revue_air_c68_c69_c84_c85_v92_2026-09-24.md), sections pertinentes du
   [journal du 13](journaux/journal_2026-09-13.md), de
   [l'archive du 9](archives/taches_archive_2026-09-09.md) et des journaux liés par les tâches.
   Les étiquettes « ouvert » historiques ne suffisent pas à rouvrir un chantier.
3. Suivre les branches et contrats appelant/appelé. Pour chaque constat : fichier et lignes
   exactes au SHA revu, déclencheur concret, défaut/réglage exposé, conséquence et preuve.
   Séparer bug confirmé, hypothèse à mesurer et choix utilisateur explicite.
4. Exécuter seulement les tests ciblés utiles au constat ; rapporter commandes et résultats.
   Une revue statique ne lance pas automatiquement de partie. Toute correction ultérieure
   suit la matrice de validation d'AGENTS.md ; aucun bénéfice économique n'est déduit des tests.
5. Enregistrer `docs/revue/2026-09-26_lot_XX.md` avec : référence, fonctions/plages lues,
   constats priorisés, anciens constats reclassés, tests, limites et point exact de reprise.
   Mettre à jour la ligne de revue dans les tâches avec les lots terminés et le prochain lot.
   Relire le diff et exécuter `rtk proxy git diff --check`, puis **arrêter la passe**.

## Commande de reprise à donner dans une nouvelle conversation

> Exécute uniquement le lot 01 du plan docs/revue_code_2026-09-26_plan.md.
> Respecte le plafond de lecture ; subdivise si nécessaire. Revue sans correctif ni campagne.
> Enregistre le rapport, actualise le suivi et arrête-toi après cette passe.

Remplacer `01` par le prochain lot ou sous-lot indiqué dans le dernier rapport.
