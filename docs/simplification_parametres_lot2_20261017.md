# Simplification des paramètres — lot 2 (préparation, 17/10/2026)

Suite de l'[inventaire du 16/10](inventaire_parametres_20261016.md). Le **lot 1** (en cours, branches
`v222-purge-air` agy et `v222-purge-terrain` grok) retire les 6 réglages « reliquat / effet absent »
et les constantes figées à `false` ; `air_p0_second_step_marginal` et `air_p0_margin_probe` sont
retirés par l'utilisateur.

Le lot 2 vise les **options OFF au défaut dont le verdict est déjà négatif ou nul** dans
`docs/taches.md`. Les retirer ne change pas le défaut : validation = contrats + smoke 1×1
(+ règle opcodes si le diff touche un chemin chaud). **Aucun retrait sans accord utilisateur
sur la liste** : un OFF n'est pas un réfuté (cf. légende de l'inventaire).

## Prérequis à trancher par l'utilisateur

1. **Fin de compatibilité `c121_air_economics=0`.** C121 est « définitivement adopté » (taches.md,
   12/10, retrait C119). Tant que le toggle existe, toute la famille C99–C115 reste atteignable
   ([plan C115](air_c115_cleanup_plan_20261010.md)). Décider : retirer le toggle C121 lui-même,
   puis toute la chaîne legacy AIR.
2. **Fil rail seul du 14/10** : les variantes V177–V194 ont été mesurées en rail seul 10×3 (bruit
   élevé). Les déclarer closes ou les garder comme briques d'expérience ?
3. **Sondes** (55 réglages `Sonde, OFF`) : hors lot 2. Ce ne sont pas des réglages morts ; une
   éventuelle fusion dans le masque `probes` est un chantier distinct.

## Lot 2A — AIR legacy pré-C121 (si prérequis 1 accepté)

| Réglages | Verdict | Source |
|---|---|---|
| `c99_air_speed_api_fix`, `c100_air_trip_physical`, `c101_…`, `c103_…`, `c105_…`, `c106_…`, `c108_…`, `c109_…`, `c110_…`, `c112_…`, `c114_air_c100_full_replay` (+ sondes C104, C111, C113) | Remplacés par C121 ; aucun consommateur sous C121=1 | plan C115 du 10/10 |
| `c121_air_economics` (toggle lui-même) | Adopté définitivement le 12/10 | taches.md l.85 |
| `c84_air_target_fleet` | Réfuté (−69,6 k£/an) | taches.md l.884 |
| `c85_air_equipment_frontier` | Caduc sous V96 | taches.md l.884 |
| `c122_air_threat_retry` | 40×5 `fail_primary` (−9,9 k£/an) | taches.md l.91 |
| `v133_air_build_retry` | Réfuté (porte A) | taches.md l.920 |
| `v134_air_p2p_saturated_hub` | Réfuté (porte A) | taches.md l.919 |
| `c83_local_repair` (+ `c83_fixes`, `c83_preempt_open` à vérifier) | 20×10 et 40×3 `fail_primary`, « prototype OFF conservé » | taches.md l.181, l.874 |

⚠️ Pièges connus : `C69_TRACK_BUILDS` et `c69BuildDates` (Save/Load) sont partagés ; ne garder
`OpexC104BestAirEngine`, `OpexC69ComputeKDec/CachedKDec` qu'après grep des appelants.

## Lot 2B — rail (si prérequis 2 accepté)

| Réglages | Verdict | Source |
|---|---|---|
| `v181_rail_max_trains` | 0 clonage, identique au bit près | taches.md l.1190 |
| `v185_rail_short_freight_pct` | Négatif (−44,7 k) | l.1186 |
| `v187_rail_refleet_during_search`, `v188_rail_join_slopes` | −126,7 k, 3/7 | l.1189 |
| `v190_rail_double_build`, `v190_rail_double_delay`, `v190_rail_max_trains` | Plantage puis nul ; défauts 0 maintenus | l.1191, 1202, 1339 |
| `v192_rail_time_denom_pct` | Nul confirmé | l.1203 |
| `v193_chain_towns` | Nul | l.1199 |
| `v194_short_to_served_dst` | Nul (−17 k) | l.1201 |
| `v131_rail_repair`, `v131_town_clearance` | Réfuté (porte A 40×5) | l.935 |
| `rail_cached_proximity_gate` | Porte A 40×5 `fail_primary` | l.877 |
| `rail_depot_cost` | 40×3 `fail_primary`, chantier différé | l.811 |
| `rail_origin_reuse` + 10 sous-réglages | Rail seul 10×3 neutre/négatif | l.1250 |

**À ne pas retirer sans avis** : `v180_*` (porte A échouée mais encore citée), `v182_*` (« reste
meilleure »), `v177_*`, `v207_*` (défauts sur branche V207), `v197/v198/v199/v200` (worktree
`wt-v197-dbl` vivant), `v163_multi_cargo` (« gros banc à faire »), `v171_rail_knots`,
`rail_geometry_*` (« non qualifié », pas réfuté).

## Lot 2C — autres réfutés

| Réglages | Verdict | Source |
|---|---|---|
| `capital_quote_learning` | Rejeté (P0 09/10) | l.214 |
| `v139_feeder_bus` | Réfuté (porte A 40×5) | l.931 |

À vérifier avant de proposer : `town_growth*`, `road_pax_build*`, `v88_*` (V218 a réutilisé V88),
`c80_*`, `air_efficiency_*`, `exp_*`, `v92/v93_*` (V93 plancher qualifié : ne pas confondre avec
`v93_air_demand_production`).

## Exécution proposée

- Un agent par lot, un worktree chacun, après fusion du lot 1 (mêmes fichiers `info.nut` /
  `settings.nut` : éviter les conflits). 2A et 2B touchent des fichiers disjoints hors
  `info.nut`/`settings.nut`, donc parallélisables ; 2C à l'un des deux.
- Même consigne qu'au lot 1 : garder exactement le défaut, refuser et justifier tout retrait qui
  toucherait Save/Load ou un appelant partagé, mettre à jour `sweeps/` (plans, tests de contrat),
  aucun banc lancé par l'agent.
- Validation par Claude : relecture du diff, contrats, smoke 1×1 ; pour 2A (gros retrait sur un
  chemin AIR), 20×10 neutre selon la règle opcodes avant fusion.
