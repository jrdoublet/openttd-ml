# OpexAI — carte de lecture du code courant

**30 septembre 2026, lecture statique ; aucune qualification runtime nouvelle.**
[Index](README.md) · [Tâches](taches.md) · [Invariants](../AGENTS.md)

Ce guide remplace comme point d'entrée les [schémas historiques](architecture_opexai.md),
pas les contrats détaillés des modules. Le code local comporte des corrections
non exécutées : consulter le suivi avant de le considérer comme référence.

## Pipeline et responsabilités

| Couche | Modules sous `ai/OpexAI/` | Contrat à vérifier avant modification |
|---|---|---|
| Entrée / réglages | `main.nut`, `info.nut`, `settings.nut`, `globals_pre.nut`, `globals_post.nut` | Déclaration, quatre difficultés, chargement et usages cohérents ; pas de changement implicite de défaut |
| Information / candidats | `catalog.nut`, `candidates.nut`, `spatial.nut` | Moteurs/cargos via API ; génération et fraîcheur du vivier distinctes de sa sélection |
| Économie / financement | `economy.nut`, `projects.nut`, `capital.nut`, `budget.nut`, `tension.nut` | Profit attendu/calibré, capital disponible, dénominateur C69, priorité défensive et revalidation ; pas simple classement au revenu |
| Construction | `builder_rail.nut`, `builder_air.nut`, `air_recovery.nut`, `builder_road.nut`, `builder_water.nut` | Devis et exécution distincts ; échecs partiels, ressources réutilisées et récupération AIR R19 locale non validée |
| Exécution / ordonnanceur | `scheduler.nut`, `scheduler_tasks.nut`, `orchestrator.nut`, `task_*.nut` | Tâches, intentions réactives et workers reprenables ; budget d'opcodes par tick, pas stock cumulable |
| État / événements | `events.nut`, `event_handlers.nut`, `lines.nut`, `persist.nut` | Invalidation ciblée, identité des lignes, Save/Load et réconciliation après lecture des réglages |
| Mesure | `probes.nut`, `ledgers.nut` | Activation effective, coût de sonde, formats des panneaux et correspondance avec les décodeurs |
| Cartographie / recherche | `terrain_map.nut`, `water_graph.nut`, `task_terrain.nut`, `pathfinder_v90/` | C67 disponible sans consommateur métier adopté ; pathfinder rail segmenté, stock worker expérimental |

Le portefeuille compare nouvelles lignes et renforts sous les filtres du chemin
actif. `fundScore` est une heuristique d'allocation ; seul le protocole apparié
peut qualifier un gain. Ne pas appliquer une seconde calibration à une marge déjà
observée (R2 local, validation encore due). L'état économique initial, sa révision
après construction et sa restauration sont trois endroits à examiner ensemble.

## Ordre de chargement

`main.nut` importe `pathfinder.rail` v1. `globals_pre.nut` précède les helpers :
budget, catalogue, économie, spatial, terrain/connectivité, candidats, tension,
projets, pathfinder V90, builders rail/air/eau/route, puis `globals_post.nut`.
`builder_air.nut` charge transitivement `air_recovery.nut` : vérifier aussi ces
dépendances, pas seulement la liste directe de `main.nut`.

Les définitions `OpexAI::...` sont chargées **après la classe** : capital, événements,
handlers, ledgers, lignes, orchestrateur, persistance, sondes, scheduler/dispatch,
puis tâches air/projets/rail/rapport/route/terrain/ville/eau. Lire les `require`
effectifs avant tout déplacement ; cette carte ne remplace pas leur ordre.

## Limites et liens utiles

- Eau courante : BFS borné `OpexWaterFindConnection`, **pas Lakes/lib_water**.
- Route : bus et camions, `policy_road` ; anciens réglages individuels retirés.
- Rail : financement 100 distinct de terrain 170 ; conserver accélération C41.
- AIR : distinguer legacy, replay C115 et expériences C121. C115 protégé ;
  aucune nouvelle activation autorisée par ce guide.
- Save/Load implémenté ne signifie pas que chaque état est couvert en jeu.
  R5/R19/R20 locaux nécessitent encore leurs parcours moteur, notamment la file
  de récupération AIR et les aéroports réutilisés.
- [C80](18_orchestrateur_double_registre.md), [cartographie](c67_cartographie_contrat.md),
  [catalogue C121](catalogue_decoupe_phase2_20260929.md),
  [rechargement](19_rechargement_partie.md) : conception et chronologie détaillées.
- Bancs : `sweeps/bench_v2.py`, `run_c66_reference.py`,
  `bench_1v1_5y_20seeds.py` ; compteurs, santé et gel dans `physical_counters.py`,
  `game_health.py`, `campaign_freeze.py`. [Guide GitHub](bancs_github.md).