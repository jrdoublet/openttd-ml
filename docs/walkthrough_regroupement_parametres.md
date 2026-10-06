# Walkthrough : Regroupement des Politiques et Suppression des Pistes Abandonnées

> **Date** : 2026-09-17  
> **Chantiers réalisés** :
> 1. Élimination formelle de **66 paramètres de pistes abandonnées** de [`ai/OpexAI/info.nut`](../ai/OpexAI/info.nut) et verrouillage neutre dans [`ai/OpexAI/settings.nut`](../ai/OpexAI/settings.nut).
> 2. Regroupement de ~60 réglages adoptés en **8 macro-politiques** `policy_*` déballées proprement dans `settings.nut`.
> 3. Bascule du défaut de `air_early_slot` à 1 (conforme à la décision économique du 2026-09-15).
> 4. Réduction nette de **-1 870 lignes de code** et passage de **169 à 44 paramètres exposés** dans `info.nut` (-74%).
> 5. Validation intégrale : **119 tests unitaires réussis**, équivalence bit-à-bit vérifiée par smoke test Docker.

---

## 1. Contexte et Motivations

Après le regroupement réussi des 70 sondes de diagnostic en 9 macro-sondes `probe_*` (faisant passer `info.nut` de 230 à 169 paramètres), l'interface de configuration de l'IA restait encombrée de dizaines de paramètres historiques :
- Des branches d'exploration rejetées ou abandonnées au fil des bancs de tests (ex. `rail_prequote` -30,7% de valeur, `portfolio_fresh_budget` -27,3%, `c46_freight_grid`, `c48_indexed_regeneration`, `c55_*_origin_relax`, l'architecture `water_lakes_*` C57, etc.).
- Des shims de compatibilité morts (ex. `rail_min_distance`, `event_vehicle_autoreplaced`).
- Des réglages économiques et techniques adoptés à 100% sur bancs officiels 20×10 qui n'ont plus aucune raison d'être désactivés individuellement par l'utilisateur.

Ce chantier applique le principe architectural des macro-sondes aux paramètres de politiques, tout en éliminant les paramètres morts.

---

## 2. Table des 66 Pistes Formellement Abandonnées (Retirées de `info.nut`)

Chacun de ces réglages a été retiré de `info.nut`. Dans `settings.nut`, la variable globale correspondante est explicitement assignée à sa valeur neutre (`false`, `0`) pour garantir qu'aucune dépendance de code Squirrel ne soit rompue :

| Paramètre retiré | Défaut | Motif de l'abandon / Justification factuelle |
|---|:---:|---|
| `rail_min_distance` | 25 | Mort : ignoré dans le code, bornes cinématiques `catalog.bounds` utilisées |
| `event_vehicle_autoreplaced` | 1 | Mort : description dit "deprecated compatibility setting, value is ignored" |
| `rail_prequote` | 0 | Rejeté : -30,7% de valeur en 5×6 apparié (P1) |
| `rail_prequote_keep_plan` | 0 | Rejeté avec `rail_prequote` |
| `rail_terrain_probe` | 0 | Rejeté avec `rail_prequote` |
| `portfolio_fresh_budget` | 0 | Rejeté : -135,5 k£/an, valeur -27,31% en 5×6 apparié (`docs/taches.md` B6) |
| `portfolio_dynamic_batch` | 0 | Rejeté : surconsommation d'opcodes démontrée (`docs/taches.md` P2) |
| `dynamic_batch_reject_limit` | 3 | Rejeté avec `portfolio_dynamic_batch` |
| `dynamic_batch_ops_budget_pct`| 50 | Rejeté avec `portfolio_dynamic_batch` |
| `portfolio_floor_pct` | 0 | Rejeté : banc 20×10 post-09/09 défavorable (-4,94% valeur, 4V/16D) |
| `tension_scoring` | 0 | Rejeté : vecteur de tension Liebig abandonné au profit de `clean_density_score` |
| `shadow_pricing` | 0 | Rejeté : prix d'ombre dual C35.4 abandonné |
| `decision_friction_permille` | 50 | Rejeté avec `tension_scoring` / `shadow_pricing` |
| `flat_bonus` | 0 | Supprimé au défaut : bonus forfaitaires historiques x1.89 / x1.60 |
| `road_cheap_trace` | 0 | Banni : C37 cheap L-corridor |
| `road_multistop` | 0 | Non adopté : dédoublement d'arrêts routiers inefficace |
| `marginal_fleet` | 0 | Non adopté : dimensionnement marginal initial |
| `road_pax_extensions` | 0 | Désactivé après banc officiel 20 graines |
| `c50b_road_cap_relax` | 0 | Rejeté : C50b extension de flotte routière à 8 véhicules |
| `c50b_rail_backlog_relax` | 0 | Rejeté : C50b suppression du seuil de backlog |
| `c46_freight_grid` | 0 | Non adopté : grille spatiale fret cartésienne |
| `c46_freight_grid_shadow` | 0 | Non adopté avec `c46_freight_grid` |
| `c48_indexed_regeneration` | 0 | Non adopté : 10V/10D au banc C48 final, gain non démontré |
| `c48_index_shadow` | 0 | Non adopté avec `c48_indexed_regeneration` |
| `c49_variable_denominator` | 0 | Non adopté : rapport négatif `docs/06_denominateur_variable.md` |
| `c55_freight_origin_relax` | 0 | Rejeté : C55 relaxation d'origine fret réfutée |
| `c55_road_origin_relax` | 0 | Rejeté : C55 relaxation d'origine route réfutée |
| `c55_road_pax_origin_relax`| 0 | Rejeté : C55 exemption d'origine pax réfutée |
| `c41_rail_lost_signal_repair` | 0 | Non adopté : réparation signaux suite à VehicleLost |
| `c41_rail_lost_junction_repair` | 0 | Non adopté : réparation jonctions suite à VehicleLost |
| `station_join` | 0 | Abandonné : raccordements de gares Phase 2 supplantés par `air_joined_stops` |
| `join_max_distance` | 0 | Abandonné avec `station_join` |
| `join_place` | 0 | Abandonné avec `station_join` |
| `basin_share` | 0 | Abandonné avec `station_join` |
| `astar_cost` | 0 | Non adopté : table TrainLineAI 13.4 conservée contre coûts 15.3 |
| `reborrow` | 0 | Abandonné : ré-emprunt d'un palier de dette non mesuré |
| `pax_near` | 0 | Sonde théorique : admission de profits négatifs pour diagnostic |
| `probe_negative` | 0 | Sonde théorique : construction forcée de projets déficitaires |
| `air_demand_cap` | 0 | Rejeté 2 fois : plafonnement de flotte par production captée |
| `air_demand_plan` | 0 | Rejeté : -51,5% de profit_year en 20×10 (`bench_air_demand_plan_10y`) |
| `air_margin_v2` | 0 | Non adopté : abaissement des marges de trésorerie aériennes |
| `reserve_maint_cap` | 0 | Non adopté : plafonnement de la réserve à 1 mois de maintenance |
| `air_presite` | 0 | Non adopté : pré-test des deux sites d'aéroports avant engagement |
| `air_split_feeder_test` | 0 | Non adopté : test causal de rabattement split |
| `air_abandon_site` | 0 | Non adopté : mémoire d'abandon par site exact |
| `air_town_limit_memory` | 0 | Non adopté : cooldown municipal sur `ERR_STATION_TOO_MANY` |
| `water_site_catalog` | 0 | Rejeté par bench : le rescannage historique reste le gagnant |
| `water_discovery_real_fronts` | 0 | Rejeté : fronts réels de quais |
| `water_lakes_connectivity` | 1 | Architecture MinchinWeb.Lakes formellement abandonnée (`docs/taches.md` C57) |
| `water_lakes_ops_budget` | 1 | Architecture MinchinWeb.Lakes formellement abandonnée (`docs/taches.md` C57) |
| `c39_engine_refresh` | 0 | Non adopté : reconstruction catalogue sur `EngineAvailable` |
| `c41_water_refresh` | 0 | Non adopté : rafraîchissement catalogue eau sur `EngineAvailable` |
| `c41_water_precheck` | 0 | Non adopté avec `c41_water_refresh` |
| `c41_road_refresh` | 0 | Non adopté : rafraîchissement catalogue route sur `EngineAvailable` |
| `loop_budget` | 0 | Non adopté : vidage continu d'opcodes sans sleep (surconsommation CPU) |
| `growth_yields` | 0 | Non adopté : dépense de croissance urbaine subordonnée aux projets |
| `pricing_road_rating` | 0 | Non adopté : application de la courbe de gare au bus |
| `pricing_rail_depot` | 0 | Non adopté : compte du dépôt rail dans le coût modélisé |
| `fleet_fix` | 0 | Inopérant / redondant dans le code livré |
| `event_depot_sell` | 0 | Non adopté : vente immédiate au dépôt |
| `event_industry_close` | 0 | Non adopté : stop-loss immédiat fermeture d'industrie |
| `event_subsidy_probe` | 0 | Non adopté : sonde passive sur offres de subvention |
| `c42_subsidies` | 0 | Non adopté : conversion des offres de subventions en candidats |
| `event_vehicle_lost` | 0 | Non adopté : alerte spécifique convois perdus |
| `c60_town_rating_filter` | 0 | Non adopté : filtre proactif municipal avant recherche de site |
| `air_cadence_cap_adaptive`| 0 | Non adopté : désactivation cadence sur cartes pauvres |
| `air_max_distance` | 0 | Inerte (0 = illimité) |
| `air_full_load` | 0 | Non adopté : chargement complet avion |
| `c53_order_noload` | 0 | Non adopté : OF_NO_LOAD fret |
| `feeder_candidates` | 0 | Inactif : candidats dédiés supplantés par arrêts joints |
| `fleet_before_new` | 0 | Non adopté : expansion de flotte avant nouvelle ligne |
| `transit_cost` | 0 | Inerte (0 = pas de pénalité) |
| `infra_amort_pct` | 0 | Inerte (0 = coût réel OpenTTD) |
| `portfolio_max_batch` | 1 | Fixé à 1 (comportement unitaire historique) |
| `air_fleet_buffer` | 0 | Fixé à 0 (tampon neutre) |
| `feeder_hub_wait_max` | 100 | Fixé au seuil nominal (100 pax) |
| `feeder_hub_min_days` | 60 | Fixé au délai nominal (60 jours) |

---

## 3. Table des 8 Macro-Politiques Adoptées

| Macro-paramètre (`info.nut`) | Défaut | Variables Squirrel pilotées dans `settings.nut` | Description |
|---|:---:|---|---|
| `policy_caches` | 1 | `C41_ROAD_FREIGHT_SERVED_INDEX`, `C41_ROAD_FREIGHT_ACCEPTANCE_INDEX`, `C41_RAIL_PAX_CRUISE_CACHE`, `C41_RAIL_FREIGHT_CRUISE_CACHE`, `C41_RAIL_FREIGHT_ACCELERATION_CACHE`, `C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE`, `C41_RAIL_CASH_RELEASE`, `PORTFOLIO_CACHE`, `AIR_SITE_CACHE_ENABLED` | Caches de calcul et index de vitesse/accélération/chalandise C41 & C36.1 |
| `policy_feeders` | 1 | `FEEDER_ENABLED`, `FEEDER_UNLOCK`, `FEEDER_PRICING`, `FEEDER_PORTFOLIO`, `FEEDER_TOWN_COVERAGE`, `FEEDER_MAIL_DUPLICATE`, `FEEDER_MAIL_STRICT_ORDERS`, `FEEDER_HUB_CHECK` | Rabattement multimodal urbain vers les hubs aéroports/gares C29/C32 |
| `policy_rail` | 1 | `RAIL_DEVIS`, `RAIL_SEARCH_RESUMABLE`, `RAIL_MICRO_DEADLINE`, `RAIL_SEGMENTED_SEARCH`, `RAIL_REFLEET`, `DYNAMIC_PATHFINDER_CAP`, `PAX_FULL_LOAD`, `ORIGIN_SITABLE` | Recherche A* reprenable, devis réel AIAccounting, doublement saturé, ordres |
| `policy_road` | 1 | `ROAD_BUILD_ENABLED`, `ROAD_REFLEET`, `ROAD_FLEET_FIX`, `PRICING_ROAD_OPS`, `ROAD_PAX_OVERLAP`, `ROAD_PAX_VOIRIE` | Construction routière, arrêts sur voirie existante, dédoublement, anti-doublon |
| `policy_air` | 1 | `AIR_PORTFOLIO`, `FLEET_PORTFOLIO`, `AIR_CADENCE_CAP`, `AIR_FLEET_LINE_PRICE`, `AIR_ROI_ORDER`, `AIR_ABANDON`, `AIR_MARGIN`, `AIR_CHEAP_SITE`, `AIR_JOINED_STOPS`, `AIR_HUB`, `AIR_HUB_FIX` | Portefeuille aérien, filtre empreinte C36.3, cadence de piste, arrêts joints |
| `policy_abandon` | 1 | `ABANDON_MEMORY`, `ABANDON_GEN_FILTER`, `ABANDON_MEMORY_TRANSIENT_GUARD` | Mémoire d'échecs de construction et filtrage précoce des candidats C22/C33 |
| `policy_portfolio` | 1 | `ECONOMY_FIX`, `CLEAN_DENSITY_SCORE`, `STAGED_BOOTSTRAP`, `VIVIER_RATIO_FILTER`, `COMPLEX_CARGO`, `CAPITAL_CALIBRATION`, `DYNAMIC_CASH_RESERVE`, `C53_ORDER_NONSTOP`, `EVENT_CATALOG_INVALIDATE` | Invariants de sélection financière, cascade bootstrap, fret secondaire |
| `policy_vehicle_events` | 0 | `EVENT_VEHICLE_CRASHED`, `EVENT_VEHICLE_UNPROFITABLE` | Gestion événementielle C52 : crashs, véhicules déficitaires chroniques |

---

## 4. Inventaire des 44 Paramètres Exposés

Le catalogue exposé dans `info.nut` comprend désormais exactement 44 paramètres, répartis en 4 groupes lisibles :

1. **Système & Persistance (4)** : `debug_signs` (1), `decision_log` (0), `save_full_state` (1), `pathfinder_sleep_ticks` (0).
2. **Sondes de diagnostic unifiées (9)** : `probe_cost`, `probe_scheduler`, `probe_candidates_road`, `probe_candidates_rail`, `probe_catalogue`, `probe_rail_search`, `probe_vehicle_lost`, `probe_portfolio`, `probe_events` (toutes à 0 par défaut).
3. **Macro-politiques adoptées (8)** : `policy_caches` (1), `policy_feeders` (1), `policy_rail` (1), `policy_road` (1), `policy_air` (1), `policy_abandon` (1), `policy_portfolio` (1), `policy_vehicle_events` (0).
4. **Calibrations physiques & options réelles de jeu (23)** :
   - Trésorerie & Opcode : `loan_repay_floor_k` (300), `pathfinder_hard_cap_k` (10), `abandon_cooldown_days` (365).
   - Rail & Portefeuille : `rail_terrain_factor` (170), `project_top_k` (64), `project_top_k_dynamic` (0), `rail_expand` (0, B5).
   - Route : `road_pax_build` (0), `road_loading_fix` (0), `road_time_scaled_cap` (0, B3), `road_pax_catchment_pct` (86), `road_stop_catchment_houses` (10), `road_pax_dwell_days` (6).
   - Air : `air_early_slot` (1, adopté 15/09), `air_early_slot_target_towns` (6), `air_early_slot_min_pop` (1000), `air_early_slot_bonus_pct` (50), `air_fleet_cadence_days` (7), `air_joined_stop_limit` (2), `air_pax_revenue_calibration_pct` (104).
   - Municipal & Flotte : `town_growth` (1), `town_growth_skip_noop` (0), `unprofitable_streak_threshold` (3).

---

## 5. Résultats des Vérifications

### 5.1 Tests Unitaires (Docker)
Exécution de l'intégralité des suites de tests du dépôt sous conteneur :
```bash
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 -m unittest sweeps/test_campaign_freeze.py sweeps/test_b3_road_fleet_targets.py sweeps/test_b5_rail_persistence.py sweeps/test_b9_air_catchment.py sweeps/test_m3_equipment_roi.py sweeps/test_game_health.py sweeps/test_m1_measurement_truth.py sweeps/test_review_residual_contracts.py sweeps/test_b7_water_guards.py sweeps/test_c46_shadow.py sweeps/test_scheduler_task_contract.py sweeps/test_b6_portfolio_causality.py sweeps/test_physical_counters.py sweeps/test_b8_scrap_lifecycle.py sweeps/test_b4_feeder_orders.py
```
*Résultat* : **119 tests exécutés, 119 tests passés (OK)**.

### 5.2 Validation Physique (Smoke Tests Docker)

1. **Équivalence bit-à-bit stricte avec le contrôle historique** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[air_early_slot=0]" --seeds 42 --years 1 --out /tmp/smoke_early0.json
   ```
   *Résultat* : `value=325332 score=226 profit=254888 st_rating=175.0 veh=25 st=24 status=OK`  
   **Identité absolue au bit près** avec le résultat d'avant nettoyage.

2. **Équivalence bit-à-bit avec les 7 macro-politiques explicites** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[policy_caches=1,policy_rail=1,policy_road=1,policy_air=1,policy_feeders=1,policy_abandon=1,policy_portfolio=1,air_early_slot=0]" --seeds 42 --years 1 --out /tmp/smoke_macro.json
   ```
   *Résultat* : `value=325332 score=226 profit=254888 st_rating=175.0 veh=25 st=24 status=OK`  
   **Identité absolue** confirmant que le déballage dans `settings.nut` active rigoureusement les mêmes drapeaux.

3. **Exécution nominale avec `air_early_slot=1` adopté** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI" --seeds 42 --years 1 --out /tmp/smoke_run.json
   ```
   *Résultat* : `value=288306 score=221 profit=236589 st_rating=175 veh=27 st=29 status=OK`  
   Exécution fluide, 29 gares construites et 27 véhicules en circulation.
