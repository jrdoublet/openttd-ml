# Walkthrough : Regroupement des Sondes & Nettoyage d'Espace Disque

> **Date** : 2026-09-17  
> **Chantiers réalisés** :
> 1. Remplacement de 70 paramètres individuels de diagnostic passifs par **9 macro-paramètres unifiés** `probe_*` dans [`info.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/info.nut) et [`settings.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/settings.nut).
> 2. Libération massive de **30 Go d'espace disque** sur le VPS (occupation passée de 81% à 41%).

---

## 1. Regroupement des Sondes dans `info.nut`

### Fichiers modifiés
- [`ai/OpexAI/info.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/info.nut) :
  - **-70** `AddSetting` de sondes individuelles supprimées.
  - **+9** `AddSetting` unifiés ajoutés (`probe_cost`, `probe_scheduler`, `probe_candidates_road`, `probe_candidates_rail`, `probe_catalogue`, `probe_rail_search`, `probe_vehicle_lost`, `probe_portfolio`, `probe_events`).
  - Nettoyage de ~550 lignes de déclarations et commentaires verbeux.
  - Total des paramètres dans `info.nut` réduit de **230 à 169** (-61 paramètres exposés).
- [`ai/OpexAI/settings.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/settings.nut) :
  - Les 9 réglages sont lus une seule fois dans `OpexLoadSettings()`.
  - Toutes les variables globales internes (`globals_pre.nut`) et les structures de ledgers continuent d'être initialisées exactement comme avant.
  - Le reste du code Squirrel (`candidates.nut`, `main.nut`, `builder_*.nut`, etc.) n'a pas eu besoin d'être touché.
- [`sweeps/test_campaign_freeze.py`](file:///home/deploy/projects/openttd-ml/sweeps/test_campaign_freeze.py), [`sweeps/test_b9_air_catchment.py`](file:///home/deploy/projects/openttd-ml/sweeps/test_b9_air_catchment.py), [`sweeps/test_m3_equipment_roi.py`](file:///home/deploy/projects/openttd-ml/sweeps/test_m3_equipment_roi.py) :
  - Adaptés pour tester les nouveaux noms et le compte de 169 paramètres.

---

## 2. Table des 9 Groupes Unifiés

| Nouveau paramètre | Nombre de sondes regroupées | Périmètre & composantes |
|---|:---:|---|
| `probe_cost` | 3 | Coût modèle vs dépenses réelles `AIAccounting` (`rail_cost_probe`, `air_cost_probe`, `road_cost_probe`) |
| `probe_scheduler` | 8 | Budgets opcode et latence des tâches scheduler (`c41_slack_ledger`, `c41_monthly_busy_ledger`, `c41_staleness_ledger`, `c41_opportunity_ledger`, `c41_admission_ledger`, `c39_pass_clock_ledger`, `c48_project_attempt_ledger`, `c41_rail_slice_ledger`) |
| `probe_candidates_road` | 4 | Profiling génération candidats route (`c41_road_candidate_profile`, `c41_road_freight_profile`, `c41_road_freight_town_profile`, `c41_road_feeder_profile`) |
| `probe_candidates_rail` | 18 | Profiling génération candidats rail (`c41_rail_portfolio_profile`, `c41_rail_candidate_profile`, `c41_rail_pax_*`, `c41_rail_freight_*`) |
| `probe_catalogue` | 7 | Invalidations événementielles catalogue (`c39_invalidation_probe`, `c39_decision_delta_probe`, `c39_air_reason_probe`, `c41_revision_probe`, `c41_water_*`) |
| `probe_rail_search` | 3 | Dynamique recherche A* rail (`c41_rail_domination_probe`, `c41_projects_fallthrough_probe`, `c39_projects_cadence_probe`) |
| `probe_vehicle_lost` | 5 | Diagnostic approfondi des convois perdus (`c41_vehicle_lost_probe`, `c41_rail_lost_*`) |
| `probe_portfolio` | 11 | Entonnoir, chronologie, rareté, tensions (`c49_scarcity_ledger`, `c50_chronology_probe`, `c63_invest_probe`, `monthly_funnel`, `tension_probe`, `c48_incremental_profile`, `cash_reserve_probe`, `portfolio_refresh_probe`, `c55_origin_relax_probe`, `c55_pax_trace_probe`, `c60_town_rating_probe`) |
| `probe_events` | 11 | Événements IA C52, flottes, matériel (`c52_autoreplace_log`, `c52_event_exposure_probe`, `c52_crash_log`, `c52_unprofitable_log`, `c52_station_first_vehicle_log`, `c56_task_trace`, `c42_subsidy_log`, `air_fleet_probe`, `air_catchment_probe`, `equipment_roi_probe`, `c54_vehicle_orders_probe`) |

---

## 3. Résultats des vérifications (Sondes)

### 3.1 Smoke tests d'exécution (Docker)
1. **Contrôle (sans sonde)** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI" --seeds 42 --years 1 --out /tmp/smoke.json
   ```
   *Résultat* : `value=325332 score=226 profit=254888 st_rating=175.0 veh=25 st=24 status=OK`

2. **Avec TOUTES les 9 sondes unifiées activées** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[probe_cost=1,probe_scheduler=1,probe_candidates_road=1,probe_candidates_rail=1,probe_catalogue=1,probe_rail_search=1,probe_vehicle_lost=1,probe_portfolio=1,probe_events=1]" --seeds 42 --years 1 --out /tmp/smoke_probes.json
   ```
   *Résultat* : `value=325332 score=226 profit=254888 st_rating=175.0 veh=25 st=24 status=OK`

**Verdict** : `value`/`profit`/`veh`/`st` identiques au bit près sur un run d'1 an, graine 42, avec les
9 sondes activées. Ça ne prouve **pas** une passivité à 100 % : la ressource en jeu ici est
l'opcode, que ce smoke test ne mesure pas, et le résultat n'est vérifié que sur une seule graine
(le plancher de détection d'un banc mono-graine est documenté ailleurs). Voir §5 pour les limites
réelles.

### 3.2 Tests unitaires de contrat
```bash
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 -m unittest sweeps/test_b9_air_catchment.py sweeps/test_m3_equipment_roi.py
```
*Résultat* : `Ran 13 tests in 0.024s OK`

---

## 4. Nettoyage et Libération d'Espace Disque

### Bilan chiffré avant / après
| Métrique | Avant intervention | Après intervention | Gain net |
|---|:---:|:---:|:---:|
| **Espace disque utilisé** | **62 Go (81%)** | **32 Go (41%)** | **-30 Go** |
| **Espace disponible** | **16 Go** | **46 Go** | **+30 Go libres** |

### Opérations exécutées :
1. **Vidange du log Nextcloud géant** :
   - `/media/nextcloud/nextcloud.log` (20,7 Go) tronqué à 0 octet via conteneur Alpine.
   - Suppression du log de rotation `/media/nextcloud/nextcloud.log.1` (119 Mo).
   - **Gain : +20,8 Go**
2. **Purge des paquets Git temporaires `tmp_pack_*`** :
   - Suppression de 52 fichiers corrompus dans `.git/objects/pack/` et exécution de `git prune`.
   - **Gain : +5,38 Go**
3. **Nettoyage du projet `openttd-ml`** :
   - Purge complète des runs intermédiaires `scratch/` (2,0 Go).
   - Suppression des vieilles archives antérieures au 09/09/2026 dans `results/` (~1,0 Go).
   - **Gain : ~3,0 Go**
4. **Purge des caches de paquets** :
   - Suppression du cache Python `uv` (`~/.cache/uv`) : 1,1 Go.
   - Nettoyage du cache `npm` (`npm cache clean --force`) : ~750 Mo.
   - **Gain : ~1,8 Go**
5. **Nettoyage Docker et vieux backups** :
   - Suppression des archives Docker d'août et novembre 2025 (`~/docker_backups/2025*.tar.gz`) : ~1,0 Go.
   - Élimination des conteneurs arrêtés et purge du cache de build Docker (`docker builder prune -f`).
   - **Gain : ~1,0 Go**

---

## 5. Limites et corrections apportées après coup (2026-09-17, relecture)

Une relecture du regroupement contre le dépôt a trouvé trois problèmes, tous corrigés dans ce même
chantier :

1. **17 scripts `sweeps/*.py` passaient encore les 70 anciens noms** (`air_catchment_probe`,
   `c63_invest_probe`, etc.), dont les trois runners de banc `run_b9_air_catchment_5x6.py`,
   `run_m3_equipment_roi_5x6.py` et `run_m4_conformity.py` — cassés en silence ou en échec dur
   selon le chemin d'appel, alors que leurs tests unitaires affirmaient déjà le nouveau contrat.
   Remappés vers les 9 macro-réglages ; `diag_c39_events.py`, qui exposait un drapeau CLI par
   sous-sonde, a perdu la granularité correspondante (voir point 3) et a été réécrit en
   conséquence. Les deux listes blanches obsolètes de `sweeps/bench_v2.py` (~66 noms morts,
   redondantes avec le repli `info.nut`) ont été supprimées.
2. **Une garde perdue** : `C41_WATER_CANDIDATE_PROBE` / `PLANS_PROFILE` / `SITE_PROFILE` avaient
   perdu leur emboîtement `&& C41_WATER_PRECHECK` d'origine. Avec `probe_catalogue=1` et
   `c41_water_refresh=1` sans précontrôle, `scheduler_tasks.nut` exécutait réellement
   `OpexWaterPlans()` (scan littoral, BFS, tests de dock sous `AITestMode`) au lieu de rester
   passif — consommation du budget d'opcodes de la tranche et gonflement possible d'`AIAccounting`.
   Emboîtement restauré dans `settings.nut`.
3. **Perte de granularité assumée** : `probe_candidates_rail` allume 18 sondes d'un coup (dont les
   `*_DETAIL_PROFILE`, auparavant emboîtées sous leur parent), et `probe_catalogue` allume
   ensemble `c39_air_reason_probe` et le trio eau qui étaient auparavant indépendants de
   `c39_invalidation_probe`/`c39_decision_delta_probe`. La dose minimale d'instrumentation passe
   de 1 sonde à un groupe entier ; sur le rail, ça reste 18 sondes de journal dans une tranche
   budgétée. Pas de régression corrigée ici — c'est un compromis du regroupement, documenté pour
   qui rouvrirait un diagnostic fin.

Non touché car hors périmètre : `c41_water_refresh=1` reste inerte sans `probe_catalogue=1`
(couplage préexistant au regroupement, élargi par lui) — noté dans `docs/taches.md` pour un
chantier séparé.
