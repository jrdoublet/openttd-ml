# Profil d'opcodes sous C121 (2026-10-02)

Diagnostic, pas un banc d'adoption. Aucun défaut modifié, aucun commit.

- **Worktree / branche** : `.wt_opprofile`, `codex/opcode-profile-c121`, depuis `52ab555` (HEAD de
  `c121-catalog`).
- **Bras** : C121 (`c121_air_economics=1,c121_catalog_incremental=1`) en duel contre AAAHogEx-115,
  graines 42/100/999/1234/5678 × 6 ans, Docker plafonné (3 CPU, 2 Go, sans swap), 3 workers.
  - `reference` : + `probe_loop_ops=1,probe_scheduler=1,catalog_cost_probe=1` ;
  - `light` : + `probe_loop_ops=1,catalog_cost_probe=1` (contrôle de perturbation).
- **Sorties** : `results/opprofile_c121_5x6_20261002.{json,profile.json,artifacts}` (10/10 parties
  saines ; `complete=false` uniquement parce que `sweeps/analyse_opcode_profile.py` a été créé
  pendant la campagne : aucun fichier existant n'a changé, vérifié par hash) et
  `results/opprofile_tg_5x6_20261002.*` (sous-profil `town_growth`, bras léger, 5/5 saines,
  `complete=true`).
- **Outils** : sonde `probe_loop_ops` (défaut 0 ; copie instrumentée de la boucle principale dans
  `OpexAI::_mainLoopProfiled`, `probes.nut`), lanceur `sweeps/diag_opcode_profile.py`
  (`OPPROF_ONLY_LIGHT=1` pour un seul bras), analyseur `sweeps/analyse_opcode_profile.py`.

## 1. Budget : l'IA est saturée toute la partie

- ≈ 6 800 ticks d'IA par an (18,5 par jour, cf. `docs/05_cadence_projects_rail_search.md` §4.3),
  soit **≈ 67,5 M opcodes par an**.
- Reliquat perdu au `Sleep(1)` : 0,9 à 2 M par an (**1,5 à 3 %**). 170 à 430 tours de boucle par
  an : un tour dure 16 à 40 ticks.
- Conséquence : tout opcode économisé est immédiatement réutilisé par une autre tâche (A* rail,
  catalogue, passage `projects`). Il raccourcit la cadence de décision ; il ne dort pas.

## 2. Répartition (bras `reference`, moyenne par graine, M opcodes)

Postes disjoints. Tâches de file : registre C39 annuel (publié par `report` en début d'année
suivante, réattribué à l'année écoulée), tranche A* retirée.

| Poste | 1970 | 1972 | 1974 | 6 ans | Part |
|---|---:|---:|---:|---:|---:|
| Recherche A* rail (tranches) | 15,4 | 19,1 | 22,7 | 116,4 | 29 % |
| Catalogue (tâche de file + reprises C121 dans le tick) | 22,6 | 19,2 | 7,2 | 75,8 | 19 % |
| Passages `projects` | 19,2 | 13,3 | 7,5 | 64,5 | 16 % |
| `town_growth` | 2,3 | 9,5 | 18,2 | 62,7 | 15 % |
| Régénérations (réactive `regen` + travailleur `regen_candidates`) | 12,3 | 7,5 | 2,1 | 44,2 | 11 % |
| `report` (bilan annuel) | 0,3 | 1,8 | 2,8 | 11,0 | 3 % |
| `air_fleet` | 0,0 | 0,7 | 2,8 | 8,2 | 2 % |
| Constructions réactives C77 (`c77_build`, `c77_subsidy`) | 4,3 | 1,3 | 0,3 | 7,9 | 2 % |
| Échantillonneur C117 (hors file, tous les 2 jours) | 0,2 | 0,8 | 2,0 | 6,5 | 2 % |
| Reliquat perdu au `Sleep(1)` | 1,9 | 1,0 | 1,1 | 7,8 | 2 % |
| Budget | 67,8 | 68,0 | 68,6 | 405,9 | |

Sous-postes (sondes `catalog_cost_probe`, 6 ans) :
- **Catalogue AIR** (`AIR_LIGHT`) 55,2 M : `new_pairs` 15,6 ; `hub_site` 13,5 ; `hub_discover` 11,9 ;
  `hub_hub` 10,5 ; `sites` 2,5 ; préparation 0,7 (tri des villes compris). Les bras hub (36 M)
  coûtent plus que les paires neuves, visées jusqu'ici.
- **Passages `projects`** (`PROJECTS_COST`) : construction 33,4 M (attente des commandes comprise,
  voir §5), régénération 27,3 M (dont 13,7 M de `staged_full` en 1970).
- **Sélection** (`SELECTION_LIGHT`) : 24,0 M (resélection 10,9 ; complète 8,6 ; incrémentale 4,5).
- **C117** : 1,5 k opcodes par échantillon en 1970, 24 k en 1975 (bras léger : 32 k).

Le bras léger donne la même structure (orchestrateur 45 à 60 M/an, C117 6,1 M, reliquat 7,7 M ;
reprises du catalogue 64 M au lieu de 40 M).

## 3. `town_growth` : la planification qui échoue

Sous-profil (bras léger, 5 × 6 ans, `results/opprofile_tg_5x6_20261002.*`) :

| | 1970 | 1971 | 1972 | 1973 | 1974 | 1975 |
|---|---:|---:|---:|---:|---:|---:|
| `OpexRoadPlanFor` (M) | 2,0 | 5,3 | 8,5 | 11,5 | 15,1 | 14,2 |
| Planifications / an | 17 | 28 | 39 | 48 | 59 | 49 |
| Opcodes / planification (k) | 118 | 191 | 219 | 239 | 258 | 290 |
| Villes construites (M opcodes) | 0,4 | 0,3 | 0,5 | 0,5 | 0,3 | 0,3 |
| `OpexTownBusPaxServed` (M) | 0,02 | 0,15 | 0,18 | 0,27 | 0,27 | 0,21 |

- **95 % du coût de la tâche est la planification de lignes qui ne se construisent pas** (≈ 1
  construction par an). `OpexTownBusPaxServed` (hypothèse initiale) est négligeable.
- La mémoire `town_growth_plan_memo` ne retient l'échec qu'à nombre de maisons identique : une
  ville qui grandit est replanifiée à chaque passage.
- Suspect principal, **non mesuré** : dans `OpexRoadSites` (`builder_road.nut:151`), chaque tuile
  du balayage en anneau (rayon 16, jusqu'à 1 089 tuiles, deux appels par plan) parcourt la liste
  complète de nos tuiles d'arrêt de bus (`OpexRoadOurBusTiles`, arrêts joints aux aéroports
  compris) **avant** les filtres bon marché (cargo, constructible, plat).

## 4. Inventaire tris et filtres Squirrel (remplaçables ou allégeables)

Classés par poids mesuré. « Exact » = mêmes sorties, donc mêmes décisions.

| Site | Poids mesuré | Proposition | Exact |
|---|---|---|---|
| `OpexRoadSites` (`builder_road.nut:151`) : balayage en anneau + exclusion O(tuiles × arrêts) | dans `OpexRoadPlanFor`, 56,5 M / 6 ans | Tester l'exclusion après les filtres purs ; restreindre la liste d'exclusion aux arrêts à moins de `2·rayon + distance minimale` du centre ; préfiltrer par `AITileList` + `Valuate(AITile.GetClosestTown)` | oui (l'ordre de l'anneau et le compteur de sondes sont conservés) |
| `_resizeAirFleets` (`task_air.nut:754`) : `airLines.sort(OpexAirFleetPriorityCompare)` à chaque passage | `air_fleet` 2,8 M/an en 1974 | Calculer `OpexAirFleetYield` une fois par ligne puis trier sur le champ (mêmes comparaisons, même permutation) | oui |
| `OpexAirStationCatchmentProduction` (`air_coverage.nut:241`) : somme tuile par tuile avec un appel API par tuile | dans la demande C121 (bras hub 36 M) ; part non isolée | `Valuate(AITile.GetCargoProduction…)` + `KeepAboveValue(0)`, puis somme des valeurs | oui |
| `air_construction.nut:98` : double boucle rectangle + `sort` des arrêts joints | par aéroport construit (rare) | `AITileList` rectangle + `Valuate` + `KeepAboveValue(0)`, en gardant l'ordre x puis y avant le tri | oui si l'ordre d'entrée est conservé |
| `OpexAirSortedTowns` (insertion O(n²)) + tri C121 des villes (`air_planning.nut:337/363`) | « préparation » 0,7 M / 6 ans | sans objet | — |
| Tris de petite taille : moteurs C121 (`air_economics_c121.nut:1106`), arrêts (`air_coverage.nut:325`), cargos (`candidates.nut:63`), paires voirie (`builder_road.nut:571`), rapport > 400 candidats (`task_report.nut:1214`) | négligeable ou rare | sans objet | — |
| Rebalayages `AIStationList(STATION_AIRPORT)` (`projects_selection.nut:56/76/110`, `air_towns.nut:175`, `air_coverage.nut:231`, `task_projects.nut:1011`) | ~30 opcodes par aéroport et par appel | cache par passage si un profil le justifie | oui |

Hors tri : l'échantillonneur C117 (2 M/an en fin de partie) peut garder en mémoire par avion le
moteur, les capacités et le coût d'exploitation, et sauter le courrier à capacité nulle (exact).

## 5. Limites

- `OpexOpsMeasureEnd` compte 10 000 opcodes par tick traversé, y compris un tick passé à attendre
  une commande de construction : les postes « construction » sont des bornes hautes.
- `probe_scheduler` perturbe la trajectoire (journal par sélection) ; le bras léger sert de témoin.
- Le registre C39 et P5 n'enregistrent que la dernière tranche A* d'un passage ; le total A* reste
  cohérent avec les itérations finales × ≈ 2 600 opcodes (écart < 10 %).
- 5 graines × 6 ans en duel : ordres de grandeur, pas d'effet causal.
